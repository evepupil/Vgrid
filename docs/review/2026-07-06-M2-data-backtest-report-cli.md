# Review：M2（data + backtest + report + cli）

- **区间**：`cff3707` → `0c65f11`（HEAD），共 5 个 commit：data / backtest / report / cli / docs
- **范围**：`src/vgrid/{data,backtest,report,cli}/**`、`core/models.py` 与 `strategy/engine.py` 在本区间的配套小改、`tests/test_{provider,cache,loader,akshare_provider,matcher,metrics}.py`、`examples/159920.json`
- **门禁**：`pytest` 82 passed / `mypy` clean（41 files）/ `ruff` clean，全绿；`[project.scripts] vgrid` 已注册

> 说明：M1 的 6 个问题（见 [_剩余问题.md](./_剩余问题.md) ① 的 1–6）本次 review 确认**均未处理**——`engine.py` 仅改了 `_execute_sell`（填 `realized_pnl`），`roadmap.md` 仅改了里程碑行，`.gitattributes` 仍不存在。下面只列 M2 新发现。

---

## 发现的问题

### 1. `_covers` 按首末日期判断覆盖，检测不出区间内的数据空洞（中）

**位置**：`src/vgrid/data/loader.py:62-66`

```python
def _covers(bars, start, end) -> bool:
    if not bars:
        return False
    return bars[0].ts.date() <= start and bars[-1].ts.date() >= end
```

只看缓存里最早和最晚两根 K 线的日期能不能包住 `[start, end]`，中间有没有缺日子完全不管。一旦某次 fetch 返回的序列本身就不连续（akshare 偶发缺日、代理中断拿到部分数据、或上游接口异常），这个洞会永久留在缓存里，之后任何"首末能包住"的请求都会被判命中、直接切片返回**残缺数据**，回测在不知情下跑在不完整行情上。

实际触发概率：akshare 对连续日期区间一般返回完整交易日序列，所以不常见；但一旦发生就是"静默算错"，后果比概率严重。loader 没有交易日历，光靠 span 确实查不出来。

**建议**：至少在文档里写明这个限制（"命中 = 首末日期包住，不保证中间无缺失"）；后续接一份交易日历，在 `_covers` 里做"区间内应有多少交易日 vs 实际有多少根"的完整性校验，或在 fetch 返回根数明显少于预期时告警。

### 2. 分钟线 akshare 路径零测试、也没真实跑通（中）

**位置**：`src/vgrid/data/akshare_provider.py:52-59`（`_fetch_minute`）、`tests/test_akshare_provider.py`

`test_akshare_provider` 只 mock 了日线的 `fund_etf_hist_em`；`_fetch_minute`（调 `fund_etf_hist_min_em`、用 "时间" 列）没有任何测试。`docs/模块设计/cli.md` 自己也注明：分钟线真实下载被本机代理拦（`push2his.eastmoney.com`）没验证。等于这条路径目前"编译过、逻辑没验证"。而分钟线正是 roadmap 里 T+0 ETF 回测的关键周期。

**建议**：补一个 mock `fund_etf_hist_min_em` 的用例（参考日线那个 mock 写法），至少把"时间"列适配、分钟 ts 解析、`fetch` 返回的 `BarSeries.frame=MINUTE` 锁住。真实下载等有干净网络环境再补冒烟。

### 3. CLI 完全没做错误处理，异常直接 traceback（低-中）

**位置**：`src/vgrid/cli/app.py`（`_cmd_fetch` / `_cmd_backtest`）

两个子命令里，akshare 断网 / 接口列名变更、`--config` 的 JSON 缺字段、`GridConfig.from_dict` 校验失败、`simulate` 抛错，都会以原始 Python traceback 直接糊到用户脸上、退出码还不是干净的非零码。对一个面向人用的命令行不太够。

**建议**：把取数 / 配置解析 / 回测各包一层 try，捕获已知异常（网络、`ValueError`、`KeyError`），打印一行人话错误 + `return 1`；未预期异常再放行 traceback。

### 4. 买入持有收益的分母和网格总收益对不齐（低-中）

**位置**：`src/vgrid/backtest/metrics.py:156`（`_buy_hold` 用 `_ratio(proceeds - cost, cost)`）、报告对照列

网格 `total_return` 的分母是 `initial_cash`（全部本金）；`buy_hold_return` 的分母是 `cost`（按手取整后**实际投入**的金额 = 成交额 + 买入费，`≤ initial_cash`）。两者并排放在报告"网格策略 / 买入持有"对照列里，基准不同。手算：`initial=150`、价 `1.40` → 只买得起 100 份、`cost≈140`，10 元零头未投；此时 `/cost` 比 `/initial` 高估约 7%。本金大、价格低时差别小（手续费 + 取整零头），但严格说不在同一口径。

**建议**：`_buy_hold` 分母改用 `initial_cash`（和 `total_return` 一致），即把未投入的零头也算作"买入持有"策略的闲置资金。这样对照才公平。

### 5. 年化用 365 日历日、夏普用 252 交易日，两套日计数混用（低）

**位置**：`src/vgrid/backtest/metrics.py`

`_annualized` 用首末 K 线的**日历天数 / 365** 复利；`_sharpe` 用 `_periods_per_year`（日线 252、分钟线 252×240）`sqrt` 年化。两个都各自说得通（CAGR 走自然流逝时间、夏普走交易周期采样），但同一份报告里两个"年化"口径不一样，看报告的人容易困惑。

**建议**：在某处（报告脚注或模块文档）注明两者口径不同；或统一到一种日计数。

### 6. 缓存写入非原子，中断会留半残文件（低）

**位置**：`src/vgrid/data/cache.py:57`（`pq.write_table(table, path)` 直写目标路径）

写入过程中进程被杀 / 断电 / 磁盘满，parquet 文件就是半残的，下次 `load` 会抛错。本地缓存场景概率低，但真发生就是"缓存损坏 + 下次启动失败"，且用户不一定能定位到是缓存坏了。

**建议**：写到临时文件（如 `path.with_suffix(".parquet.tmp")`）再 `os.replace` 原子替换。

### 7. 单次 fetch 内若出现重复 ts，`BarSeries` 会直接抛错（低）

**位置**：`src/vgrid/data/provider.py`（`bars_from_columns` 返回 `list[Bar]`）→ `akshare_provider.py:40` / `cache.py:52` 构造 `BarSeries`

`bars_from_columns` 只排序不去重；`BarSeries.__post_init__` 要求 ts **严格**递增，遇重复就抛 "必须按时间严格递增"。日线 ETF 基本不会重复；但分钟线跨段拼接时 akshare 偶尔会返回重复时间戳，目前会直接崩。loader 的 `_merge` 只在"缓存 × 新下"之间按 ts 去重，单次 fetch **内部**不去重。

**建议**：要么在 `bars_from_columns` 里按 ts 去重（后到覆盖前到，和 `_merge` 口径一致），要么把这个失败语义写进文档。

---

## 已核实"看起来像 bug、其实不是"的点

- **撮合"每根 K 线先 low 后 high"是不是过度乐观**：核实后认为对网格是合理的。网格挂的是限价单，只要价格触到就成交，而一根 K 线的 low/high 都被定义成真实触及过的价位，所以 `[low, high]` 区间内的所有网格线在本根内被触发是符合实盘的。先 low 后 high 的顺序只影响引擎内部的 `last_price` 中间态，由于两端都喂了，净成交集合与真实触及集合一致。不是 bug。（假设已在 backtest.md 写明。）

## 小结

M2 把 data / backtest / report / cli 端到端串起来了，门禁全绿，`Fill` 加 `realized_pnl` 是为支撑胜率/盈亏比的干净小改。主要问题集中在**数据可信度**（#1 区间空洞静默、#2 分钟线未验证、#7 重复 ts 崩溃）和**用户面**（#3 CLI 错误处理、#4 对照列口径、#5 日计数）。其中 #1、#2 建议优先：一个关乎回测结果是否可信，一个关乎一条核心周期路径根本没被验证过。
