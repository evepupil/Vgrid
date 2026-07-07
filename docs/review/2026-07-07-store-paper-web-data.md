# Review：M4+（store / paper / web / 新数据源 / analysis + 清 backlog）

- **区间**：`f95719f` → `43629d5`（HEAD），共 60 个 commit
- **性质**：范围最大的一次——开发先清掉前三次 review 的 19 条 backlog（`eb52589`/`dfecb60`/`d8a73d4`/`d76b554`/`2b94663`/`16300d8`/`b87c79d`），随后落了 store（SQLite）、paper（模拟盘）、一整个 web 后端 + Vite/React 前端、新数据源（sina/tencent/mootdx）、analysis（网格适配评分 + 黑天鹅推演）
- **范围**：`src/vgrid/{store,paper,web,analysis}/**`、`data/{akshare,tencent,mootdx,provider,cache,loader}.py`、`cli/app.py`、`strategy/ladder_view.py`、`backtest/{matcher,metrics,result}.py` 的改动，及对应测试。前端 `frontend/**`（tsx/css）按项目规范是展示层，只肉眼审、不逐行抠
- **门禁**：`pytest` 257 passed / `ruff` clean，但 **`mypy` 红——16 个错**（`tests/test_stress.py` 13 个 + `tests/test_scan_api.py` 3 个，根因是测试帮手把返回类型标成 `object`）。门禁没全绿，见 #30

> 用了三个并行子代理深读 paper/store、web 后端、analysis+新数据源；HIGH 和中等的几条我都自己复核过代码。子代理的"核实通过"清单见文末。

---

## 〇、backlog 核实（19 条）

开发在 review 记录里标了"已解决"，我逐条核实——**不是糊弄，全部改对了**：

| 区间 | 结果 |
|---|---|
| M1 #1–6 | 全 ✅ continue→break（`engine.py:177`）、desired_orders 改纯只读（去掉 `ensure_covers_down_to`）、删 `extend_levels_down` 单实现、roadmap+`requires-python` 锁 3.13、补等比/守卫/`down_amount_factor<1` 测试、`.gitattributes` 统一 LF |
| M2 #7 | ⚖️ 取舍（`_covers` 离线无日历源，已写进 docstring + `refresh=True` 绕过） |
| M2 #8–13 | 全 ✅ 分钟线 mock 测试、`_guard` 错误处理、买入持有分母改 `initial_cash`、报告加年化口径脚注、缓存 `.tmp`+`os.replace` 原子写、`bars_from_columns` 按 ts 去重 |
| M3 #14–19 | 全 ✅ calmar 加 `annualized_return>0` 守卫、`ScanSpec` 校验未知字段 + fixed/vary 重叠 + 候选值去重、`--top` 双层 `max(0,…)` 钳制、`run_scan` 加进度回调 + 主路径测试 |

下面只列本次新发现。

---

## 发现的问题

### 20. 默认日线源 sina 不复权；缓存键不区分 source/adjust（高）

**位置**：`src/vgrid/data/akshare_provider.py:48,65`（默认 `source="sina"` → `fund_etf_hist_sina`）、`src/vgrid/data/cache.py:42`（文件名 `{symbol}_{frame.value}.parquet`）

`AkshareProvider()` 默认走 sina，交叉核对 akshare 1.18.64 源码：`fund_etf_hist_sina` 直接解析新浪 `klc_kl.js`，**全程没有 adjust 参数、返回原始不复权价**。只有 `source="em"` 才 `adjust="qfq"`（腾讯默认也是 qfq）。ETF 一旦分红，除权日会有一根"凭空暴跌"的 K 线，回测收益直接算错。

更糟的是缓存键 `{symbol}_{frame}.parquet` **不带 source/adjust 维度**，`loader._merge` 又是 incoming 覆盖 existing：把 sina（不复权）和 em/腾讯（前复权）的数据合并到同一个 parquet，旧段保留旧基准、新段是新基准，拼接处价格跳空，`_covers` 还会把这种残缺缓存判成命中。即使始终用同一个 qfq 源，"今天取的 qfq"和"下个月取的 qfq"基准本身就会漂移（前复权以最新价为锚），合并落盘同样错位。

**建议**：默认源改成 `em`（qfq）；缓存键带上 source/adjust（或记录复权基准日），跨基准合并时告警或拒绝。至少在文档显著位置写明"sina 默认不复权、有分红 ETF 别用"。

### 21. `process_tick` 非原子事务，崩一半会让 fills 表与引擎状态发散（中）

**位置**：`src/vgrid/paper/runner.py:86-94`、`src/vgrid/store/repository.py:38,61`

`save_tick` 和每个 `save_fill` 各自调一次 `conn.commit()`。一个 tick 产生多笔 fill（中枢建仓 / 向上突破重建 / 连续买卖）时，进程在 `save_tick` commit 后、某次 `save_fill` commit 前崩，DB 里 tick 进去了但 fill 只进了一部分。重启 `replay` 用 **tick** 重建引擎（runner.py:73-79，只 `load_ticks` + `engine.start/step`，不写 fill），引擎状态永远正确；但 **fills 表缺行**——`snapshot.n_fills`（runner.py:129 读 fills 表）低估，任何对 `fills.realized_pnl` 求和的审计/展示都 ≠ `engine.realized_pnl`。"持久化账本平仓时 cash_flow == realized_pnl"这个不变量在崩过后就破了，而且静默。

**建议**：把一个 tick 的 tick + 全部 fills 包进单事务，末尾一次 commit。

### 22. tick 用 ts 当 PK + INSERT OR REPLACE + ORDER BY ts，但 ts 非单调（中）

**位置**：`src/vgrid/store/db.py:18`、`repository.py:34-43`

`tick` 表 `ts TEXT PRIMARY KEY`，`save_tick` 用 INSERT OR REPLACE，`load_ticks` 按 ts 字典序返回，ts 来自 `datetime.now()`。引擎按**到达顺序**处理（单线程轮询），但 replay 按 ts 排序。NTP 跳变 / DST 让 `datetime.now()` 回退时，replay 的顺序与原跑不一致 → 引擎状态发散；同 ts 撞车时后一条覆盖前一条 tick 行，前一条产生的 fills 却留在表里（无级联删）。

**建议**：tick 表加 `AUTOINCREMENT` 序号列，按序号排序与去重，别用 wall-clock ts 当唯一键。

### 23. akshare 的 NaN 单元格让整个报价接口崩溃或渗进 JSON（中）

**位置**：`src/vgrid/web/quotes.py:54,65,72` + `_dec:86-92`

`_dec` 用 `Decimal(str(v))`，对 NaN 返回的是 `Decimal('NaN')`（构造不抛异常，try/except 拦不住），不是 None。后果：
- `最新价` 是 NaN → `price > 0` 抛 `InvalidOperation` → `_row_to_quote` 崩 → `fetch_many` 整个失败 → `/api/quotes` 和 `/api/watchlist/enriched` 返回空 + 错误，**一个标的的某行坏数据让整个关注列表/顶部行情条空白**。
- 只有 `昨收`/`涨跌额`/`涨跌幅` 是 NaN → `price - prev_close` 同样抛；或侥幸没抛的字段以字符串 `"NaN"` 混进 JSON，前端拿到"看起来是数字、其实是 'NaN'"的字段。

**建议**：`_dec` 里构造完判一下 `d.is_finite()`，NaN/Infinity 一律返回 None。

### 24. GET `/api/state?db=...` 会建文件，路径还不校验（中）

**位置**：`src/vgrid/web/routes/state.py:22-23` → `store/db.py:39` `connect()`

`connect()` 调 `sqlite3.connect(path)`（文件不存在就建）+ `executescript(_SCHEMA)`。任何带 `db` 路径的 GET 请求都会作为副作用在磁盘上凭空生成一个空 sqlite 库（然后返回 404 "no data"）。`db` 参数也没校验——`db=../../foo.sqlite` 之类路径遍历可行。

**建议**：GET 不该有建库副作用；校验 `db` 路径在允许目录内、拒绝不存在文件（要建库走显式 POST/部署接口）。

### 25. 改了运行中策略的配置会静默脱节，且没有重部署路径（中）

**位置**：`src/vgrid/web/strategy_deploy.py:87-125`、`paper/runner.py:62-63`

`PUT /api/strategies/{name}` 后文件是新参数，但运行中的 `PaperRunner` 引擎用的是启动时的配置（内存），DB 也还是旧配置（`PaperRunner.__init__` 配置不符就拒）。再 `POST /{name}/deploy` 会因为 DB 已存在抛 `FileExistsError`。没有"停止 → 重建 → 重部署"的 API，要应用编辑得手动删 `paper/<mode>/<name>.sqlite`。`/api/strategies/enriched` 于是把新的文件参数和旧实例的夏普并列展示，自相矛盾。

**建议**：要么编辑运行中策略时拒绝并提示先停实例；要么提供 stop/redeploy 接口，把内存引擎、DB、文件三者一起换新。

### 26. strategies create/update 只 catch ValueError，缺字段抛 KeyError → 500（中）

**位置**：`src/vgrid/web/routes/strategies.py:67-81`

`GridConfig.from_dict` 缺必填字段（`symbol`/`lower_price`/…）时抛 `KeyError`，这两个路由只 catch `ValueError` → 500 而不是 400。`routes/backtest.py:36` 和 `routes/ladder.py:29` 都正确 catch 了 `(ValueError, KeyError)`，口径不一致。

**建议**：统一 catch `(ValueError, KeyError)`。

### 27. portfolio / strategies 路由的 `mode` 参数未校验（中）

**位置**：`src/vgrid/web/routes/portfolio.py:22,28`、`routes/strategies.py:49`

`PortfolioManager.__init__` 在 `mode` 不是 `live`/`sim` 时抛 `ValueError` → 500。部署路由做了显式校验，这两个没有。

**建议**：路由层先校验 `mode`，非法返 400。

### 28. etf_info 在 akshare 失败时未捕获，还会把 "nan" 缓存进去（中）

**位置**：`src/vgrid/web/etf_info.py:33-41`、`routes/etf.py:12-17`

`EtfInfoCache._ensure` 直接调 `ak.fund_etf_spot_em()`，akshare 宕机就 500（`/api/quotes` 同场景会捕获降级，这里没有）。`_ensure` 也没过滤 NaN 名称，某些 symbol 的缓存会静默存成 `"nan"` 字符串。

**建议**：`_ensure` 套 try，失败时用旧缓存或返 None；过滤 NaN/空名称再入缓存。

### 29. 腾讯 qfq 在 qfqday 缺/空时静默退回 day（不复权）（中）

**位置**：`src/vgrid/data/tencent_provider.py:72`

`rows = data.get(key) or data.get("day") or []`，请求 `adjust="qfq"` 时 `key="qfqday"`，该 symbol 没有 qfqday（新上市 / 无分红历史）或返回空，直接 fall back 到不复权的 `day`，不抛不告警。用户以为拿的是前复权，实际是原始价；再和 em 的 qfq 缓存混写，错位叠加。

**建议**：qfq 退回 day 要么告警要么抛错，别静默。

### 30. mypy 没全绿（低，但违反"门禁全绿才 commit"）

**位置**：`tests/test_stress.py:10-22`（`_report() -> object` 帮手）、`tests/test_scan_api.py:59,70,78`

16 个 mypy 错。`test_stress.py` 的 `_report(**kw: object) -> object` 把返回类型写死成 `object`，后续 `r.occupancy`/`r.scenarios` 全报"object 没有属性"；`test_scan_api.py` 同理对响应体当 `object` 用。**根因在测试侧的类型标注偷懒**，生产代码 `black_scan_report -> StressReport` 是带类型的，运行没问题（pytest 257 过）。但项目规则是 mypy strict、门禁全绿才 commit，开发在 review 记录里也标了"mypy clean"——这条没对上。

**建议**：`_report` 标成 `-> StressReport`、kwargs 用具体类型；scan_api 测试把响应体 cast 到具体结构。几分钟的事。

### 31. 多 writer 无 busy_timeout，web 层还有裸 connect 不开 WAL（低）

**位置**：`src/vgrid/store/db.py:39`、`src/vgrid/web/portfolio.py:154`

`store.connect()` 对文件库开了 WAL（db.py:42，好），但没设 `busy_timeout`（默认 5s），`paper run` 写、`paper serve` 里 `web/portfolio.py:154` 又自己 `sqlite3.connect`（连 WAL 都没开）混用同一文件，并发写要么 5s 后 `database is locked`，要么两个独立 engine 往 fills 表交叉插行。

**建议**：`connect()` 统一加 `PRAGMA busy_timeout=5000`；web 层别再自己裸 connect，复用 `store.connect()`。

### 32. 部署有 TOCTOU 竞态（低）

**位置**：`src/vgrid/web/strategy_deploy.py:100-113`

`db_path.exists()` + `load_config` 检查与随后的 `connect` + `save_config` 是两个独立连接周期、无锁，两个并发部署请求可能都通过检查同时写入。

**建议**：检查与写入放同一事务，或用文件锁。

### 33. etf_info 模块级缓存非线程安全（低）

**位置**：`src/vgrid/web/etf_info.py:33-41`

FastAPI 在线程池里跑同步路由，冷缓存时两个并发请求会同时触发 `ak.fund_etf_spot_em()`，且一个线程可能在 `_ensure` 填充途中读到不完整的 `_cache`。

**建议**：`_ensure` 加锁，或接受偶发重复刷新（代价小）。

### 34. `_resolve_price` 接受 inf / -inf（低）

**位置**：`src/vgrid/web/routes/ladder.py:38-45`

`Decimal("inf")`/`Decimal("-inf")` 解析时不抛 `InvalidOperation`，能过 400 校验进到 `engine.start(price)`，后续比较 / `shift_up_to` 行为未定义。

**建议**：校验 `price.is_finite()`。

### 35. fills 表无自然键 UNIQUE（低，当前非活跃）

**位置**：`src/vgrid/store/db.py:22`

只有 `seq AUTOINCREMENT` PK，没有 `(ts, side, price, shares, level_index)` 之类的 UNIQUE。当前 `replay` 不写 fills，所以不会双写；但没有任何 DB 约束拦住未来代码（给 replay 加补写、加重试循环）造成的重复行。

**建议**：加 UNIQUE 约束作防御纵深。

### 36. `PaperRunner.__init__` 不自动 replay（低，API footgun）

**位置**：`src/vgrid/paper/runner.py:47-65`

DB 已有历史时，调用方忘了先 `replay()` 就直接 `process_tick`，`_started=False` 会让 `engine.start(新价)` 把新价当起点从中枢重仓，与库里的历史完全脱节。CLI（`paper run`/`status`）和测试都调了 replay，现网不触发；但 API 层面是个坑。

**建议**：`__init__` 末尾自动 replay，或在 `process_tick` 里检测"DB 有历史但未 replay"时抛错提示。

### 37. mootdx 读 `full["volume"]` 依赖 ≥0.10，pyproject 却写 ≥0.9（低）

**位置**：`src/vgrid/data/mootdx_provider.py:63`、`pyproject.toml`

TDX 协议原生列名是 `vol`，mootdx 的 `to_data` 里有句 `if 'vol' in result.columns: result['volume'] = result.vol` 才补出 `volume`（核实 0.11.7 有）。`pyproject` 写 `mootdx>=0.9`，0.9.x 早期没这步复制的话 `full["volume"]` 会 `KeyError` 直接崩。

**建议**：`mootdx>=0.10`（或实测的最低版本），或代码里兼容 `vol` 列名。

---

## 核实通过（没问题）

- **`web/jsonify.py`**：Decimal→str、datetime→iso、Enum→.value，不丢精度不漏字段；指标计算里的 Decimal 数学不会产生 NaN（`sharpe_of` 对负方差有 sqrt 守卫、`_ratio`/`_occupancy` 有零守卫）。唯一的 NaN 渗漏是 #23 的 akshare 字符串。
- **`web/state.py` 重放**、`backtest_api`/`scan_api`/`ladder_api`/`series`/`curve`：重放与引擎读取一致、降采样对齐、杠杆口径 `equity = capital_cap + cash_flow` 与引擎约定一致。
- **路径遍历 / SPA 全匹配**：`_NAME_RE` 挡住策略名遍历；`server.py:73-83` 的 SPA 全匹配用 `is_relative_to` 且注册在所有 API 路由之后，API 优先。（`db` 查询参数的路径遍历是 #24，另一码事。）
- **`analysis/grid_fitness.py`**：评分公式方向正确（越震荡/振幅越大/穿越越多分越高），无除零（`path==0` 显式返回 1、cross_cap 有 `>0` 守卫），边界（根数<10 返 None、全平行情 score=0）合理。
- **store 的 Decimal 边界 / SQL 参数化 / config 一致性校验 / 引擎守恒 / `8d07c4e` 的 start 成交落库修复**：均核实正确，off-by-one 无。

## 小结

backlog 清得干净是这次最大的亮点——19 条全部按建议改对，没有走过场。新代码的问题集中在三处：
- **数据可信度**：#20（默认源不复权 + 缓存键不区分基准）是 HIGH，直接关系回测数字对不对，优先级最高；#29（腾讯 qfq 静默退回）是同类问题。
- **持久化账本**：#21（半写非原子）+ #22（ts 当 PK）+ #31（并发无保护）合力削弱"模拟盘账本可审计、可续跑"这个 M4 的核心承诺。
- **web 鲁棒性**：#23（NaN 崩报价）、#24（GET 建文件）、#25（策略编辑脱节）、#26/#27（输入校验）这一组，让"看盘面板"在边界输入下容易 500 或状态错乱。

建议进实盘前至少拿下 #20、#21、#23、#25——它们都会让用户在不知情下看到错的数字或崩的面板。
