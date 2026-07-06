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
- 日线 `fund_etf_hist_em`（前复权 `qfq`）、分钟线 `fund_etf_hist_min_em`。
- `_df_to_columns`：把中文列名（日期 / 时间、开盘、最高、最低、收盘、成交量）映射成标准
  `ts/open/...`；列名对不上直接抛 `ValueError`。
- akshare 的接口签名 / 列名随版本变，适配集中在本文件；真实环境跑前确认版本对得上。

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
