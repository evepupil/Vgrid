# 模块：data（行情层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：下载行情 K 线 + 本地缓存。对外只暴露 ``load_bars``，回测 / CLI 都从它取数据。
和 strategy 一样分层：**provider 取数（I/O）、cache 落盘（I/O）、格式转换是纯函数**，
后两者单测都不碰网络。

**关键决策**：
1. **统一 Bar 抽象**：日线 / 分钟线都转成 `core.BarSeries`。data 层只管「外部格式 → Bar」，
   不让上层看到 akshare 的中文列名或 DataFrame。
2. **转换逻辑只有一份**：akshare 的 DataFrame 和 Parquet 读回来的表，都先归一成「列 dict」
   再喂 `bars_from_columns`。纯函数，单测重点。
3. **缓存按 (symbol, frame) 落 Parquet，增量合并**：每次请求区间，先查缓存是否覆盖；
   覆盖就切片返回（不打网），否则下请求区间、与缓存按 `ts` 去重合并、覆盖落盘。多次请求
   逐步扩充缓存，不会反复下同一批数据。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `provider.py` | `BarProvider` 协议 + `bars_from_columns` 纯函数（列 dict → list[Bar]） |
| `akshare_provider.py` | `AkshareProvider`：调 akshare 取日线 / 分钟线，DataFrame → 列 dict |
| `tencent_provider.py` | `TencentProvider`：直连腾讯 fqkline，ETF 前复权日线（em 不稳时的稳定兜底） |
| `mootdx_provider.py` | `MootdxProvider`：通达信协议拉分钟线（1m/5m），稳定的分钟源 |
| `cache.py` | `ParquetCache`：每个 (symbol, frame) 一个 parquet 文件，存全量，读回复用 `bars_from_columns` |
| `loader.py` | `load_bars` 门面：组合 provider + cache，区间命中 / 增量合并 / refresh |

## ③ 实现细节

### provider.py（纯转换）
- `bars_from_columns(columns, frame)`：期望 keys `ts/open/high/low/close/volume`。
  `ts` 接受 str / datetime / date / pandas.Timestamp（先 `str()` 再 `fromisoformat`）；
  价格列接受任意可转 `Decimal` 的值。结果按 `ts` 升序返回。
- `BarProvider`：`fetch(symbol, start, end, frame) -> BarSeries` 协议（`runtime_checkable`），
  akshare / 未来别的源各写各的实现。

### akshare_provider.py（akshare 适配）
- 日线两源可选（`source` 参数，构造时传）：``"sina"``（默认）或 ``"em"``。
  - **sina**：``fund_etf_hist_sina``，走新浪 host，实测稳定可用（东财 host 常被代理拦）。
    **返回不复权原始价**——回测前要意识到除权缺口会影响结果。只接 ``symbol`` 一个参数、
    返回全量历史，故在本地按 ``date`` 列（先 ``astype(str)``，源里可能是 date 对象）字典序过滤
    到请求区间；symbol 要加前缀（5 开头沪市 ``sh``、其余深市 ``sz``），见 ``_sina_symbol``。
  - **em**：``fund_etf_hist_em``，前复权 ``qfq``，按 ``start_date/end_date``（``YYYYMMDD``）取数。
    数据复权、回测更准，但实测东财 ``push2his`` host 服务端静默丢弃（TLS 通、HTTP 请求后 Empty reply，
    非代理拦——补全浏览器 headers 无效），国内几乎必挂、海外也仅约 13% 成功率且触发频控后越请求越失败，
    不作主力源。要用稳定复权源走 ``TencentProvider``。
- 分钟线只有东财源（``fund_etf_hist_min_em``），不受 ``source`` 影响。
- `_df_to_columns`：把列名（em 中文 日期/时间、开盘…；sina 英文 date/open…）映射成标准
  `ts/open/...`；列名对不上直接抛 `ValueError`。两源走同一条转换，上层无感。
- akshare 的接口签名 / 列名随版本变，适配集中在本文件；真实环境跑前确认版本对得上。

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
  不限 IP，实测连接+拉取 5/5 稳定。akshare ETF 分钟线（东财）不稳、腾讯分钟线 host 也连不上，
  mootdx 是稳定分钟源。
- 支持 ``Frame.MINUTE``（1 分钟，frequency=7）和 ``Frame.M5``（5 分钟，frequency=0）。
  历史深度：1 分钟约 2.5 个月、5 分钟约 1 年 8 个月（实测 159920，2026-07）。
- 单次最多 800 根，翻页（``start`` 累加）拉全量，直到覆盖请求 ``start`` 日期；本地按
  ``[start, end]`` 过滤、跨页按时间戳去重（``keep="last"``）。
- 连接复用：首次 fetch 连接（``Quotes.factory`` 选最快服务器），后续复用；连接异常重连一次。
- 返回不复权原始价——跨除权日有缺口，复权后续用 mootdx Affair 接口做。

### cache.py（Parquet 落盘）
- 缓存目录 `~/.vgrid/cache/`，文件名 `<symbol>_<frame>.parquet`。
- 价格 / 成交量存 `string`（`Decimal` 无损往返），`ts` 存 `timestamp`。读回 `to_pydict()`
  成列 dict，复用 `bars_from_columns` 复原——和 akshare 走同一条转换路径，缓存与数据源解耦。

### loader.py（门面）
- `load_bars(symbol, start, end, frame, *, provider=, cache_dir=, refresh=False)`。
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
