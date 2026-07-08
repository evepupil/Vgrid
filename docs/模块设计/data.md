# 模块：data（行情层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：下载行情 K 线 + 本地缓存。对外只暴露 ``load_bars``，回测 / CLI 都从它取数据。
和 strategy 一样分层：**provider 取数（I/O）、cache 落盘（I/O）、格式转换是纯函数**，
后两者单测都不碰网络。

**关键决策**：
1. **统一 Bar 抽象**：日线 / 分钟线都转成 `core.BarSeries`。data 层只管「外部格式 → Bar」，
   不让上层看到各源的中文列名或 DataFrame。
2. **转换逻辑只有一份**：各源的 DataFrame 和 Parquet 读回来的表，都先归一成「列 dict」
   再喂 `bars_from_columns`。纯函数，单测重点。
3. **缓存按 (symbol, frame) 落 Parquet，增量合并**：每次请求区间，先查缓存是否覆盖；
   覆盖就切片返回（不打网），否则下请求区间、与缓存按 `ts` 去重合并、覆盖落盘。多次请求
   逐步扩充缓存，不会反复下同一批数据。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `provider.py` | `BarProvider` 协议 + `bars_from_columns` 纯函数（列 dict → list[Bar]） |
| `tencent_provider.py` | `TencentProvider`：直连腾讯 fqkline，ETF 前复权日线（**日线主力源**） |
| `mootdx_provider.py` | `MootdxProvider`：通达信协议拉分钟线（1m/5m），稳定的分钟源 |
| `mootdx_client.py` | `MootdxConnection`：通达信共享连接（建连 + 复用 + 重连一次），bars/quotes/stocks 共用 |
| `mootdx_quotes.py` | `MootdxQuotes`：实时报价（现价/昨收）+ 全市场名称，替代东财 `fund_etf_spot_em` |
| `cache.py` | `ParquetCache`：每个 (symbol, frame) 一个 parquet 文件，存全量，读回复用 `bars_from_columns` |
| `loader.py` | `load_bars` 门面：组合 provider + cache，区间命中 / 增量合并 / refresh；默认源按周期路由 |

> **行情源收敛（2026-07-08）**：`akshare_provider.py` 已删。东财（em）**K 线接口**（日线
> `fund_etf_hist_em` / 分钟 `fund_etf_hist_min_em`，走 `push2his.../kline`）实测被对端秒断
> （`RemoteDisconnected`，0.4s 直接 reset），新浪（sina）返回不复权价，两个 akshare 源做 K 线都不可靠。
> 现只留两个稳定源：**日线走腾讯前复权、分钟走 mootdx 通达信**；实时报价 / 名称也从东财现货表换成 mootdx。
>
> **东财不是整个不通，是分接口的（2026-07-08 实测）**：被封的只有上面那两个 **K 线/历史行情**接口；
> 东财的**基金分红**（`fund_fh_em` / `fund_fh_rank_em`）、**场内净值**（`fund_etf_fund_info_em`）、
> **ETF 实时现货全表**（`fund_etf_spot_em`）走的是另外的 host/path，**都通**。所以：K 线继续用腾讯/mootdx；
> M7 红利对比要的分红 / 净值照用东财；`fund_etf_spot_em` 留作 mootdx 报价的备选兜底源（暂不接）。
> 别再把结论笼统写成「em 不通」——准确说是「**东财 K 线接口不通**」。

## ③ 实现细节

### provider.py（纯转换）
- `bars_from_columns(columns, frame)`：期望 keys `ts/open/high/low/close/volume`。
  `ts` 接受 str / datetime / date / pandas.Timestamp（先 `str()` 再 `fromisoformat`）；
  价格列接受任意可转 `Decimal` 的值。结果按 `ts` 升序返回。
- `BarProvider`：`fetch(symbol, start, end, frame) -> BarSeries` 协议（`runtime_checkable`），
  腾讯 / mootdx 各写各的实现。

### tencent_provider.py（腾讯 fqkline 适配）
- 腾讯 ``web.ifzq.gtimg.cn/appstock/app/fqkline/get``，国内实测稳定（连续 8/8 成功）、
  首尔服务器也通，海外 IP 不被限——补 em 连不上的缺口。akshare 没封装腾讯 ETF，自己对接。
- ``param=code,day,start,end,count,adjust``：``count`` 上限 640 根（区间内 >640 取最近 640），
  故按年分段请求再合并（每年约 244 交易日，远低于上限），跨段边界按日期去重。
- 字段顺序 ``date, open, close, high, low, volume``（``close`` 在第 3 位，和标准
  ``open, high, low, close`` 不同，映射时挪位置——最容易翻车的点，单测重点覆盖）。
- ``adjust``：``qfq``（默认，前复权）/ ``hfq`` / ``""``（不复权）；不同 adjust 走 JSON 里不同 key
  （``qfqday`` / ``hfqday`` / ``day``）。
- symbol 前缀同 sina：5 开头 ``sh``，其余 ``sz``。只支持日线。

### mootdx_provider.py（通达信协议分钟线）
- 走通达信 TCP 7709 协议（``mootdx`` 库），不依赖东财/腾讯 HTTP host，服务器多可切换、
  不限 IP，实测连接+拉取 5/5 稳定。腾讯分钟线 host 连不上，mootdx 是稳定分钟源。
- 支持 ``Frame.MINUTE``（1 分钟，frequency=7）和 ``Frame.M5``（5 分钟，frequency=0）。
  历史深度：1 分钟约 2.5 个月、5 分钟约 1 年 8 个月（实测 159920，2026-07）。
- 单次最多 800 根，翻页（``start`` 累加）拉全量，直到覆盖请求 ``start`` 日期；本地按
  ``[start, end]`` 过滤、跨页按时间戳去重（``keep="last"``）。
- 连接走 ``MootdxConnection``（见下）。**只出分钟线**，日线走腾讯前复权（``loader`` 按周期路由）。
- 返回不复权原始价——分钟粒度跨除权日缺口极少见，故没接复权；要复权日线用 ``TencentProvider``。

### mootdx_client.py（通达信共享连接）
- ``MootdxConnection``：一条复用的通达信 TCP 连接。``Quotes.factory(market="std")`` 首次调用才
  建连（选最快服务器），后续复用；调用中协议 / 连接异常先断开重连一次，再失败才抛。
- 暴露三个方法，都返回 ``pd.DataFrame | None``：``bars``（K 线）/ ``quotes``（实时报价）/
  ``stocks``（证券名录）。K 线、报价、名称三处共用这一条连接，连接管理只有一份。

### mootdx_quotes.py（实时报价 + 名称）
- ``MootdxQuotes.snapshot(symbols)``：通达信 ``quotes()`` 一次批量取多标的现价 / 昨收 / 开高低，
  按请求顺序返回 ``Snapshot``（取不到的跳过）。**昨收为 0 当作缺**（停牌 / 数据缺，别算出假涨跌）。
- ``MootdxQuotes.names()``：``stocks()`` 拉沪（market=1）+ 深（market=0）全市场证券列表，合并成
  代码→名称。比只拉 ETF 现货表重（各几千只、翻页），调用方（``web.etf_info``）缓存 12h。
- 替代东财 ``fund_etf_spot_em``（海外常年超时）。名称字段通达信报价里没有，故名称走 ``stocks()``、
  报价里 ``Quote.name`` 留空（前端 ticker 缺名回落代码）。

### cache.py（Parquet 落盘）
- 缓存目录 `~/.vgrid/cache/`，文件名 `<symbol>_<frame>.parquet`。
- 价格 / 成交量存 `string`（`Decimal` 无损往返），`ts` 存 `timestamp`。读回 `to_pydict()`
  成列 dict，复用 `bars_from_columns` 复原——和数据源走同一条转换路径，缓存与数据源解耦。

### loader.py（门面）
- `load_bars(symbol, start, end, frame, *, provider=, cache_dir=, refresh=False)`。
- **默认源按周期路由**（`_default_provider(frame)`）：日线 → ``TencentProvider``（前复权）、
  分钟（1m/5m）→ ``MootdxProvider``。调用方可显式传 `provider` 覆盖（测试注入 stub）。
- **区间框定按日**（`bar.ts.date()` 与 `start/end` 比）：日线 / 分钟线统一，分钟线按交易日框区间。
- **去重按完整 `ts`**（datetime）：同一天的多个分钟线不会互相覆盖。
- `refresh=True`：跳过命中判断，强制下载请求区间并与缓存合并覆盖落盘。

## ④ 改动历史

- **2026-07-06（M2 首次实现）**：provider 协议 + 列式转换纯函数；akshare 日线 / 分钟线
  provider；Parquet 缓存（`Decimal` 以 string 往返保精度）；`load_bars` 门面（区间命中 /
  增量合并 / refresh）。单测覆盖列式转换、缓存往返与精度、loader 命中 / 合并 / refresh
  （FakeProvider 不打网）、akshare 列适配与 fetch（mock ak）。
- **2026-07-06（M4b 后：加 sina 源）**：东财 host（``push2his.eastmoney.com``）间歇被代理拦，
  日线加 ``"sina"`` 源作默认（新浪 host 稳定）。sina 返回不复权全量历史，本地按区间过滤、
  symbol 加 ``sh/sz`` 前缀；``em`` 源保留为可选（复权、更准但常被拦）。单测覆盖两源列适配、
  深沪前缀、按区间过滤（mock ak 不打网）。注意：sina 不复权 → 回测有除权缺口失真。
- **2026-07-07（加腾讯源）**：em 源实测不稳——东财 ``push2his`` 服务端静默丢弃（非代理拦，
  补全 headers 无效），国内几乎必挂、首尔服务器也仅约 13% 成功率且触发频控后越请求越失败；
  baostock 实测不收 ETF（股票有数据、4 只 ETF 全 0 行）。改接腾讯 ``fqkline``：国内稳定、
  首尔也通、支持前复权、ETF 友好。新增 ``TencentProvider``，按年分段绕开 640 根上限、
  字段顺序映射（close 从第 3 位挪到标准位置）。单测覆盖字段映射、前缀、分段合并去重、
  adjust、分钟线拒绝（mock requests 不打网）。
- **2026-07-07（加 mootdx 分钟源 + Frame.M5）**：分钟线数据源实测——akshare ETF 分钟线
  （东财 push2his）和日线 em 一样被服务端丢弃、腾讯分钟线 mkline 重定向 web3 host 连不上、
  新浪只支持 5 分钟且只能最近 5.5 个月。改用 mootdx 走通达信 TCP 协议：连接+拉取 5/5 稳定、
  不限 IP、1 分钟历史 2.5 个月、5 分钟历史 1 年 8 个月。新增 ``MootdxProvider``（1m/5m 翻页
  拉全量 + 区间过滤去重）、``Frame.M5``、``metrics._periods_per_year`` 加 5 分钟系数（252×48）。
  单测覆盖字段映射/翻页停止/区间过滤/跨页去重（mock Quotes 不打网）。mootdx 返回不复权，
  复权后续用 Affair 接口做。
- **2026-07-07（review 修复 #7/#8/#12/#13）**：`bars_from_columns` 单次数据内按 ts 去重
  （后到覆盖前到，分钟线跨段拼接遇重复时间戳不再崩）；`ParquetCache.save` 改原子写
  （`.tmp` + `os.replace`）；补分钟线 akshare mock 测试；`_covers` 只看首末查不出区间空洞的
  限制写进模块 docstring + 函数注释（完整校验需交易日历，暂作取舍不接，见 review 取舍记录）。
- **2026-07-08（行情源收敛到 mootdx + 腾讯，删 akshare）**：akshare 两源都不可靠——em 海外
  常年超时、sina 不复权，删 ``akshare_provider.py`` + 测试。日线定腾讯前复权为主力、分钟定
  mootdx，`loader` 加 `_default_provider(frame)` 按周期路由默认源。实时报价 / 名称也从东财现货表
  （``fund_etf_spot_em``）换成 mootdx：抽出 ``mootdx_client.MootdxConnection``（bars/quotes/stocks
  共享连接），新增 ``mootdx_quotes.MootdxQuotes``（``snapshot`` 现价+昨收、``names`` 全市场名录），
  ``web.quotes`` / ``paper.realtime`` / ``web.etf_info`` 三处换源。单测覆盖快照映射/保序/未知跳过/
  昨收 0 归空/名录合并/空降级（mock 共享连接不打网）。**取舍**：mootdx 只出不复权价，分钟粒度跨
  除权日缺口罕见故未接复权，需复权日线走腾讯（决策见对话，非单一源）。
- **2026-07-08（摸清东财哪些接口通 / 不通）**：为 M7 红利对比实测东财各接口，结论是**按接口分**——
  **K 线/历史行情**（`fund_etf_hist_em` 日线 / `fund_etf_hist_min_em` 分钟）被对端秒断
  （`RemoteDisconnected`，0.4s reset），这才是当初判「em 不通」的真相（当时要的正是 K 线）；
  而**分红明细**（`fund_fh_em`，全市场 ~7500 行 / 36s）、**累计分红排行**（`fund_fh_rank_em`，
  ~7674 行 / 74s）、**场内净值**（`fund_etf_fund_info_em`，按单只 / 1.8s）、**ETF 实时现货全表**
  （`fund_etf_spot_em`）**都通**。故 K 线维持腾讯 / mootdx 不变；分红 / 净值三个接口给 M7 用。
  两个分红接口是**全市场整表**（服务端不能按代码筛），M7 里要整表拉一次落缓存、本地按红利 ETF 池过滤。
