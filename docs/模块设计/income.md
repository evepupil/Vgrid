# 模块：income（红利 ETF 分红收益对比 · M7）

> 目标：不看代码就能看懂这块怎么实现。需求基准见 `docs/需求/红利ETF分红收益对比需求.md`。

## ① 设计

**职责**：把一批红利 ETF 的分红、价格走势、累计净值和费用放进同一份**离线对比报告**，
判断谁更适合长期持有 / 定投 / 网格。第一版只出 CLI + Markdown / CSV，不接模拟盘 / 实盘 / 前端。

**分层**（同全项目铁律）：
- **纯逻辑（离线可测）**：`series`（四条曲线）、`metrics`（指标 + 数据质量）、`report`（结果模型 + 编排 + 排名）、
  `universe`（池筛选）、`dividends` / `nav` 的**解析器**。
- **I/O（可注入）**：`dividends` / `nav` / `expenses` 的**抓取器**（东财 akshare）、`service` 的编排端口。

**关键决策**：
1. **四条曲线都起点归零**，直接可比可画：价格 / 价格+现金分红 / 价格+分红再投 / 累计净值。
   前三条以 `initial_cash` 满仓建仓为基准；累计净值是「含历史分红」的**校验基准**，再投与它差异
   过大时报 warning。
2. **分红再投不看未来**：发放日收现金，**下一交易日开盘**才按 `floor(现金/开盘/lot)·lot` 买回，
   扣银河费，买不满一手留现金——和网格 / 定投一个口径。
3. **费用只展示、不重复扣**：管理费 / 托管费 / 销售服务费基金每日从资产计提，公布的净值与场内价
   已内含，故真实价格 / 净值口径下不再扣一遍。第一版无可用 ETF 费率源，一律 `unknown`。
4. **要不复权价**：叠加分红必须用未复权收盘价，故日线走 `load_bars(..., adjust="")`（腾讯不复权），
   缓存与前复权分文件（`data` 层 `adjust` 维度）。

## ② 文件结构

| 文件 | 内容 | 层 |
|---|---|---|
| `models.py` | `DividendEvent` / `NavPoint` / `ExpenseInfo` 共享值对象 | 纯 |
| `series.py` | 四条起点归零收益曲线（`SeriesPoint`） | 纯 |
| `metrics.py` | `IncomeMetrics` + `DataQuality` + 指标 / 数据质量计算 | 纯 |
| `report.py` | `EtfIncomeResult` / `IncomeComparison` + `build_etf_result` 编排 + `rank_etfs` | 纯 |
| `universe.py` | `filter_dividend_etfs`：按关键词从名录筛红利 ETF | 纯 |
| `dividends.py` | 东财 `fund_open_fund_info_em(分红送配详情)` 抓取 + 解析 | I/O + 纯 |
| `nav.py` | 东财 `fund_etf_fund_info_em` 抓取 + 解析 | I/O + 纯 |
| `expenses.py` | 费用抓取（第一版默认 `unknown`） | I/O |
| `service.py` | `build_comparison` 编排：定池 → 逐只抓取 → 算结果 → 排名 | I/O |
| `combo.py` | 红利增强组合回测：分红再投 overlay + 定投 / 网格便捷封装 | 纯 |
| `report/income.py`（在 report 包） | 终端 / Markdown / CSV / 增强摘要渲染 | 展示 |

CLI：`vgrid income compare`（横向对比）、`vgrid income enhance`（单只策略 + 分红增强）。

## ③ 实现细节

### 数据源（东财哪些接口通 / 不通，实测见 data.md）
- **分红明细**：`fund_open_fund_info_em(symbol, indicator="分红送配详情")`——单只 ETF 的**全历史**每笔
  分红（510880 一次拿到 2007→今 19 笔），列 `权益登记日/除息日/每份分红/分红发放日`。
  **需求文档原写 `fund_fh_em` 是错的**：那个只有「最近一笔」（全市场 ~7500 行、每只 1~2 条）。
- **净值**：`fund_etf_fund_info_em(fund, start_date, end_date)`——单位净值 / 累计净值，按单只、约 1.8s。
- **费用**：`fund_fee_em` 对 ETF 返回空表 → 第一版 `unknown`。
- **不复权日线**：`TencentProvider(adjust="")` 经 `load_bars(adjust="")`，缓存走 `_raw` 命名空间。

**分红源覆盖（实测到位）**：`分红送配详情` 对真红利 ETF 覆盖良好——510880（19 笔）/ 515180（6 笔）/
515080（17 笔）/ 563020 红利低波（9 笔）都拿到全历史每笔分红。某只取不到分红（返回 0 行，多因代码
不存在 / 非分红基金）时判 `missing_dividend`、仍靠累计净值曲线参与排名。新浪 `fund_etf_dividend_sina`
（给累计分红、需差分成每笔、要 sz/sh 前缀）是可选备源（需求 §13 的「分红兜底」），暂不接。

### series.py（四条曲线）
- `price_curve`：`close_t/close_0 − 1`。
- `cash_dividend_curve`：份额恒定，分红发放日到账并入现金，`equity=shares·close+现金累计`。
- `reinvest_curve`：发放日收现金记 pending，**下一根开盘**买回（扣费、买不满一手转现金），无未来函数。
- `acc_nav_curve`：`acc_nav_t/acc_nav_0 − 1`。
- 分红发放日→bar 下标：首个日期 ≥ 发放日的 bar；发放日落在样本区间外（早于首日 / 晚于末日）不计。

### metrics.py（指标 + 数据质量）
- 四口径收益率取各自曲线末点；**年化 / 回撤以「分红再投」为准**（横向排名主口径）。
- 分红次数 / 每份分红 / 分红率按**除息日落在样本期内**的事件算；样本期分红金额 = 期初满仓份额 ×
  样本期每份分红；样本分红率 = 样本每份分红 / 期初价；近 12 月分红率 = 近 365 天每份分红 / 期末价。
- `DataQuality`：`price_only`（无分红无净值）/ `missing_dividend` / `missing_nav` /
  `partial`（净值覆盖 < 样本期 80% 或再投与累计净值末点差 > 15%，带 warning）/ `ok`。

### report.py（编排 + 排名）
- `build_etf_result`：算四曲线 + 指标，打包成 `EtfIncomeResult`（含样本期内分红明细）。
- `rank_etfs`：默认 `annualized → drawdown → ttm_yield → expense`（再投年化↓→回撤↑→近12月分红率↓→
  费用↑），排序键可配；多键靠从次到主的稳定排序。费用未知按大值垫底。

### service.py（编排）
- `IncomeCompareSpec`（区间 / 关键词或 symbols / 起始现金 / lot / fee / 排序键）→ `build_comparison` →
  `IncomeCompareRun`（排名 + 池规模 + 跳过的无日线代码）。
- 端口全可注入：`names_fn`（默认 mootdx 名录）、`bars_fn`（默认腾讯不复权日线）、`dividends_fn` /
  `navs_fn` / `expenses_fn`（默认东财）。测试全传替身、离线跑通整条链。

## ④ 改动历史

- **2026-07-08（M7 首次实现，分三切）**：
  - 切1 纯核心：`models` / `series`（四曲线，再投无未来函数 + 扣费 + 取整）/ `metrics`（指标 +
    五态数据质量）/ `report`（结果模型 + 编排 + 排名）。单测 22 例。
  - 切2 数据 I/O：`data` 层给 `load_bars` / 缓存加 `adjust` 维度（前复权 / 不复权分文件）；
    `universe`（池筛选）/ `dividends`（东财分红送配详情，纠正需求把源从 fund_fh_em 改成
    fund_open_fund_info_em）/ `nav` / `expenses`（unknown）。akshare 懒导入，纯解析器单测 14 例。
  - 切3 报告 + CLI：`report/income`（终端 / Markdown / CSV）+ `service`（编排）+ `vgrid income
    compare` 子命令。service 单测 4 例。
  - 实测（510880 / 515180 / 515080 / 563020 等真红利 ETF）端到端出报告：价格 / 现金分红 / 再投 /
    累计净值四口径 + 分红率 + 数据质量；分红源对真红利 ETF 覆盖到位。
  - **取舍**：费用第一版 unknown（无可用 ETF 费率源）；取不到分红的 ETF 靠累计净值参与排名；
    新浪分红备源 + 缓存分红 / 净值（按日 / 按 ETF）留作后续优化（日线已缓存、per-ETF 抓取够快）。
- **2026-07-10（M7 深化 · 增强回测上网页）**：`POST /api/income/enhance`（`web/income_api.run_income_enhance`
  + `routes/income.enhance`，复用 `service.build_enhance`，两条曲线降采样到 300 点）+ 前端 Income 页加
  「红利对比 / 增强回测」Tab：增强 Tab 选策略（定投复用 DcaForm compact / 网格从策略库）→ KPI 行
  （策略收益 / 增强 / 分红贡献 / 累计到账分红）+ `EnhanceChart`（策略灰虚 vs 增强模式色实线）。
  端到端实测 510880 月定投 2021–2024：策略 11.79% → 增强 18.68%、分红贡献 +6.89%。API 单测 2 例。
- **2026-07-09（M7 深化 · 红利增强组合回测）**：`combo.py` 把「分红再投」叠到任意策略上——
  策略在**不复权**价上跑（除权日真跌），从其逐 bar 权益反推持仓份额（`position_value/close`），
  按持仓在发放日收分红、下一开盘再投（口径「再投」，扣费、买不满一手留现金），**不改 DCA/网格引擎**。
  `dividend_reinvest_overlay` 引擎无关 + `dca_dividend_combo` / `grid_dividend_combo` 便捷封装；
  `report.render_combo_summary` + CLI `vgrid income enhance --strategy dca|grid`。
  实测 510880 月定投 2021–2024：价格口径 11.79% → 分红增强 18.68%（分红贡献 +6.89%）。单测 5 例。
  **取舍**：分红按**发放日持仓**算（严格应按权益登记日，持仓几天内变动小，近似；与 series 一致）。
- **2026-07-08（M7 web 前端）**：补 income web API + 前端页（M7 之前只有 CLI，需求 §3 原推迟）。
  - 后端：`POST /api/income/compare`（`web/income_api.py` 的 `run_income_compare` + `web/routes/income.py`），
    复用 `service.build_comparison`，返排名 rows（metrics + 四曲线降采样到 100 点，批量 ETF × 4 省带宽）
    + pool_size / skipped。
  - 前端：`Income.tsx`（左配置：关键词逗号分隔 / 或 symbols / 区间 / 起始现金 + 右排名表点行选中）
    + `IncomeChart.tsx`（uPlot 四线叠加：价格模式色实线 / 价+现分蓝虚 / 价+分再投绿实 / 累计净值灰点，
    以价格曲线交易日为 x 轴、累计净值按 day 查表对齐）+ `incomeForm.ts` + client API + `IconIncome` +
    Rail 入口（`/income`）+ App 路由 + `income.css`。
  - 门禁：ruff + mypy strict（102 文件）+ pytest 368 全过；前端 build + lint，包体 154.7KB gzip。
