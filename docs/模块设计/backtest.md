# 模块：backtest（回测层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：把行情 `BarSeries` 喂给 M1 的 `GridEngine` 跑回测，产出成交、逐 K 权益曲线、
绩效指标。**回测器只是引擎的一个驱动器，策略逻辑一行不改**——这正是 M1 把引擎做成纯
逻辑的回报：回测和未来实盘走同一套决策，杜绝「回测一套、实盘另一套」。

**关键决策**：
1. **撮合假设「每根 K 线先 low 后 high」**：`step(low)` 触发下方买单、`step(high)` 触发
   上方卖单，等价于「日内先探底后反弹」。M1 引擎按「相对上一价的涨跌」决定买 / 卖，天然
   适配，无需改引擎。建仓用首根 `open`（不偷看未来）。
2. **逐 K 权益 = 初始资金 + 累计净现金流 + 持仓按收盘价估值**。平仓后持仓估值为 0，此时
   `权益 − 初始资金 == 引擎 realized_pnl`（守恒，单测覆盖）。
3. **指标全用 Decimal**：年化 `(1+r)^(1/years)` 走 `ln/exp`，夏普走 `sqrt`，不在统计环节
   引入 float。胜率 / 盈亏比依赖每笔卖出的 `realized_pnl`。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `result.py` | `EquityPoint` / `BacktestMetrics` / `BacktestResult` 数据类 |
| `matcher.py` | `simulate(config, bars)`：撮合循环，产出 `BacktestResult` |
| `metrics.py` | `compute_metrics` 纯函数：收益率 / 年化 / 回撤 / 夏普 / 胜率 / 盈亏比 / 手续费 / 买入持有 |

## ③ 实现细节

### matcher.simulate
- 首根 `open` 调 `engine.start` 建仓；之后每根 K 线按 `low` → `high` 喂 `engine.step`。
- 成交的 `ts` 默认是 None（引擎纯逻辑不记时），matcher 用 `dataclasses.replace` 打上触发
  它的那根 K 线时间。
- 每根收盘记一笔 `EquityPoint`。`initial_cash` 缺省 = `config.capital_cap`。

### metrics.compute_metrics
- **total_return**：`(final − initial) / initial`。
- **annualized_return**：`(1+r)^(365/days) − 1`，`days` 取首末 K 线的日历天数；用
  `Decimal.ln/exp` 求幂。
- **max_drawdown**：权益曲线峰值到谷值的最大跌幅比例。
- **sharpe**：逐 K 收益率均值 / 标准差 × `sqrt(年化期数)`；日线 252、分钟线 252×240。
  无风险利率 0；标准差为 0 返回 0。
- **win_rate / profit_loss_ratio**：基于卖出成交的 `realized_pnl`。
- **buy_hold_return**：同笔资金首根开盘按手取整买入、末根收盘卖出（扣两边手续费）。

### Fill 加 realized_pnl（core 配套小改）
- `Fill` 加可选字段 `realized_pnl`：卖出成交填（卖出净收入 − 持仓成本），买入为 None。
- `engine._execute_sell` 顺算填入，供绩效统计精确算胜率 / 盈亏比。

## ④ 改动历史

- **2026-07-06（M2 首次实现）**：matcher（先 low 后 high 撮合 + 逐 K 权益 + 守恒）、
  metrics（收益率 / 年化 / 回撤 / 夏普 / 胜率 / 盈亏比 / 手续费 / 买入持有，全 Decimal）、
  result 数据类。core/models 的 `Fill` 加 `realized_pnl`、`engine._execute_sell` 填值。
  单测覆盖撮合顺序 / ts / 守恒 / 各指标手算案例。
