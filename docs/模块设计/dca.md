# 模块：dca（量化定投策略）

> 目标：不看代码就能看懂这块准备怎么实现。

## ① 设计

**职责**：提供网格之外的第二类策略：量化定投。它回答的问题很直接：同一只 ETF、同一段行情、
同一笔资金，规则化定投能不能比网格更稳、更适合长期持有。

**边界**：
1. `dca` 只做纯逻辑：定投日程、买入金额规则、持仓和现金状态计算。不读文件、不调接口、不落库。
2. 行情继续复用 `data` 的 `BarSeries`，手续费继续复用 `core.FeeModel`，份额取整继续复用
   `core.money.shares_for_amount`。
3. 第一版只做离线回测和报告对比，暂不接模拟盘、Web 启停和实盘执行。

**关键决策**：
1. **固定金额定投作为基准线**：每周 / 每月固定买入 `base_amount`，用来判断增强定投有没有真实价值。
2. **增强定投先做两类**：跌幅加码、均线偏离。它们都容易解释，也适合 ETF。
3. **信号不能偷看未来**：固定日期可以用当根 `open` 买；需要价格信号的策略，只能用历史数据算信号，
   下一根 K 线 `open` 买。
4. **定投收益要看资金时间**：除了收益 / 累计投入，还要算 `xirr`。它能更公平地处理分批投入。

## ② 第一版策略

### 固定金额定投
- 参数：`frequency`、`base_amount`、`cash_cap`。
- 规则：到定投日就买 `base_amount`，累计投入达到 `cash_cap` 后停止。
- 用途：所有定投增强规则的对照组。

### 跌幅加码定投
- 参数：`lookback_days`、`tiers`。
- 规则：计算近期高点到当前价的回撤，按档位放大投入金额。
- 示例：回撤 5% 买 1 倍，回撤 10% 买 1.5 倍，回撤 20% 买 2 倍。
- 风险：越跌越买会加速消耗现金，所以必须受 `cash_cap` 限制。

### 均线偏离定投
- 参数：`ma_window`、`below_multiplier`、`normal_multiplier`、`above_multiplier`。
- 规则：价格低于均线时多买，高于均线时少买或暂停。
- 风险：均线窗口太短会频繁切换，太长会反应慢，后续需要参数扫描辅助选择。

## ③ 暂不纳入第一版

- **固定份额定投**：每次买固定份额，价格越高花钱越多，现金压力不稳定。
- **价值平均策略**：需要目标资产曲线，可能触发卖出，状态和指标更复杂。
- **网格 + 定投混合**：需要区分长期底仓、网格仓和现金池，等单独定投稳定后再设计。
- **模拟盘 / 实盘**：第一版先用历史数据验证策略，再决定是否进入实时链路。

## ④ 回测口径

### 成交
- 固定日期定投：用当根 K 线 `open` 成交。
- 跌幅 / 均线定投：用历史 K 线算信号，下一根 K 线 `open` 成交。
- 每笔买入金额先受剩余现金上限约束，再按 100 份一手向下取整。
- 买不满一手时跳过该次定投，并记录 `skipped_count`。
- 每笔成交都扣银河 ETF 手续费：`max(0.1 元, 成交额 × 0.00005)`。

### 状态
- `cash`：剩余现金。
- `shares`：当前持仓份额。
- `invested_amount`：累计实际投入本金。
- `total_fee`：累计手续费。
- `trades`：定投买入成交列表。
- `cash_flows`：用于计算 XIRR 的现金流列表。

### 指标
- `final_equity = cash + shares × last_close`。
- `profit = final_equity - initial_cash`，用于看账户整体结果。
- `profit_on_invested = final_equity - cash - invested_amount`，用于看已投入资金赚了多少。
- `profit_rate_on_invested = profit_on_invested / invested_amount`。
- `xirr`：按每次投入时间计算真实年化收益。
- `max_drawdown`：用逐 K 权益曲线计算。

## ⑤ 配置草案

固定金额定投：

```json
{
  "type": "dca",
  "symbol": "159920",
  "frequency": "weekly",
  "weekday": 1,
  "base_amount": "2000",
  "cash_cap": "50000",
  "amount_policy": {
    "mode": "fixed"
  }
}
```

跌幅加码：

```json
{
  "type": "dca",
  "symbol": "159920",
  "frequency": "weekly",
  "weekday": 1,
  "base_amount": "2000",
  "cash_cap": "50000",
  "amount_policy": {
    "mode": "drawdown",
    "lookback_days": 120,
    "tiers": [
      { "drawdown": "0.05", "multiplier": "1.0" },
      { "drawdown": "0.10", "multiplier": "1.5" },
      { "drawdown": "0.20", "multiplier": "2.0" }
    ]
  }
}
```

均线偏离：

```json
{
  "type": "dca",
  "symbol": "159920",
  "frequency": "weekly",
  "weekday": 1,
  "base_amount": "2000",
  "cash_cap": "50000",
  "amount_policy": {
    "mode": "ma_deviation",
    "ma_window": 60,
    "below_multiplier": "1.5",
    "normal_multiplier": "1.0",
    "above_multiplier": "0.3"
  }
}
```

## ⑥ 和现有模块的关系

- `core`：复用手续费、金额量化、份额取整。后续若新增通用成交模型，优先放 `core`。
- `data`：复用历史行情加载和 Parquet 缓存。
- `backtest`：新增定投回测驱动，和网格回测一样产出权益曲线、成交和指标。
- `report`：新增定投报告和策略对比表。
- `cli`：新增定投回测入口，参数仍走 JSON 配置文件。
- `web`：第一版暂不接；等 CLI 和报告稳定后再加页面。

## ⑦ 验收标准

- 固定金额定投能在同一段 ETF 行情上跑出成交、权益曲线、手续费和最终收益。
- 跌幅加码在回撤越大时投入金额越高，并受 `cash_cap` 限制。
- 均线偏离只用历史数据算信号，成交发生在下一根 K 线。
- 定投报告能和网格、买入持有同区间对比。
- 核心逻辑有单测覆盖：日程判断、金额规则、份额取整、手续费、现金上限、XIRR。

## ⑧ 实现说明（与草案的取舍）

落地时定了三件草案没写死的事，都为「无未来函数」和「口径可比」服务：

1. **定投日撞非交易日 → 用 K 线本身当交易日历**（`schedule.map_to_bars`）。每个日历投入日映射到
   「日期 ≥ 它的第一根 K 线」，撞上周末 / 节假日自动顺延到下一个有行情的交易日，同一根 K 线最多
   买一次（去重）。这样不依赖单独的节假日日历表（正好绕开 FR-11.2 那个没接的坑）。
2. **成交口径统一在执行 K 线的 `open`，信号只用该 K 线之前的收盘**（草案对跌幅 / 均线写的是「下一根
   open」）。因为金额信号里的「当前价」用的是执行 K 线的 open（买入价，成交时已知），不碰当根
   high/low/close，所以在当根 open 成交就已经严格无未来函数，比「下一根 open」少延一根、更直观
   （周一排的投入就在周一成交，而非拖到周二）。
3. **三方对比统一口径**（`backtest.compare`）：网格一上来用满资金、定投逐步投入，两者收益率分母不同。
   对比一律用**同一笔起始现金**起步，比末权益 / 净利 / 对起始现金的收益率 / 自然日年化（CAGR，和
   网格同一份 `annualized_return`）。定投额外给「实际投入 + XIRR」两列——它的钱分批进场，只看对起始
   现金的收益率会低估资金效率，XIRR（按每笔投入时间贴现的真实年化）才反映真实回报。

> 注：`backtest.compare` 同时依赖网格和定投，层级在两者之上，**不**放进 `backtest/__init__` eager 导入
> （否则 dca→backtest.metrics→__init__→compare→dca 成环），从 `vgrid.backtest.compare` 直接引用。

## ⑨ 改动历史

- **2026-07-08（需求归档）**：新增量化定投模块设计，锁定第一版范围为固定金额、跌幅加码、
  均线偏离三类离线回测；明确成交口径、指标、配置草案和验收标准。
- **2026-07-08（M6 切1：dca 纯逻辑 + 回测核心）**：`dca/` 落地——`config`（DcaConfig + 三种金额
  规则 + from_dict/to_dict）、`schedule`（日/周/月排期 + K 线映射）、`amount`（三规则纯计算）、
  `xirr`（二分法解真实年化）、`engine.run_dca`（逐 K 回测：日程 → 金额规则 → 剩余上限/现金约束 →
  按手取整 → 扣银河费买入 / 跳过并记因 → 权益曲线 + 指标）。复用 core 手续费/取整、backtest 的
  EquityPoint/最大回撤。31 单测覆盖日程/映射/金额/XIRR/引擎。
- **2026-07-08（M6 切2：报告 + CLI）**：`report.dca`（定投终端摘要 + Markdown 报告）、`vgrid dca`
  子命令（下载 → 回测 → 报告落盘）。
- **2026-07-08（M6 切3：三方对比）**：`backtest.compare.compare_strategies`（网格 / 定投 / 买入持有
  同起始现金、同口径）+ `report.compare`（对比表）+ `vgrid compare` 子命令。`metrics._annualized`
  提为公开 `annualized_return`，三方共用一份年化口径。补对比单测（三行同口径、定投带投入/XIRR、
  买入持有基线常在、缺配置/空数据报错）。
