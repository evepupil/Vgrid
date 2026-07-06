# 模块：strategy（网格策略层）

> 目标：不看代码就能看懂这块怎么实现。

## ① 设计

**职责**：网格策略的全部决策逻辑。**纯逻辑状态机，不碰任何 I/O**。回测和模拟盘
**共用同一份引擎**，杜绝「回测一套、实盘另一套」的偏差——这是整套系统可信的地基。

**分三层，越往下越纯**：

```
gridlines.py  纯函数：只算网格线价格，无状态
    ↑
ladder.py     Ladder：维护「当前这条阶梯」的可变状态（延伸 / 上移）
    ↑
engine.py     GridEngine：策略状态机（建仓 / 配对 / 追踪 / 资金上限 / 成交结算）
```

**关键决策**：
1. **成交假设**：挂在某条网格线上的限价单，价格触到就以该线价格成交。对流动性好、
   单笔又小的 ETF 网格，这个假设贴合真实。
2. **持仓单元用「卖出目标价」做键**（`dict[Decimal, Lot]`）。每个格子同一时刻至多
   一份货，目标价天然唯一，且不受阶梯上移 / 延伸后序号变化影响——比用序号做键稳。
3. **执行层可插拔**：引擎另提供 `desired_orders(price)`，产出「当前应该挂着的限价单
   集合」，供未来实盘执行层对账下单。它和 `step` 共用同一套决策口径，不会逻辑漂移。

## ② 文件结构

| 文件 | 内容 |
|---|---|
| `gridlines.py` | `build_levels`（等差/等比）、`bottom_gap`、`extend_levels_down`（向下延伸放大）、`shift_window_up`（向上平移） |
| `ladder.py` | `GridLine` + `Ladder`：当前阶梯状态，延伸 / 上移操作 |
| `engine.py` | `GridEngine`：策略状态机 |

## ③ 实现细节

### 网格线（gridlines.py，纯函数）
- **等差**：`level_i = lower + i·(upper−lower)/count`。
- **等比**：`ratio = (upper/lower)^(1/count)`，逐个乘上去；端点精确对齐 tick。
- 量化后相邻线重合（格数过密）直接抛错。
- **向下延伸** `extend_levels_down`：从底部往下，第 k 条与上一条间距 =
  `base_gap × factor^(k-1)`。`factor=1` 均匀延伸；`factor>1` 越跌格子越宽（防无限补仓）。
- **向上平移** `shift_window_up`：价格冲破上沿后整窗上移，保持几何形状——等差按整数格
  步长移，等比按 ratio 整数次幂放大，直到价格落回窗口内。

### 阶梯（ladder.py）
- `Ladder` 持有从低到高的 `GridLine` 列表，每条线记 `price / buy_amount / depth`。
- `ensure_covers_down_to(price)`：向下延伸到「最低线不高于 price」为止——延伸多少由
  价格实际跌到哪决定，不会无限延伸。延伸线的 `buy_amount` 按 `down_amount_factor^depth`
  放大 / 缩小（越跌每格买多少的旋钮）。
- `shift_up_to(price)`：重建基准阶梯，延伸清零。

### 引擎（engine.py，核心状态机）

**驱动**：`start(price)` 建仓 → 反复 `step(price)` 喂价格 tick。

- **建仓**（`start`）：
  - 中枢 CENTER：把现价上方每个格子的份额按市价买齐做底仓（`_build_center`）。
  - 零底仓 ZERO：不买，只等下方买单。
- **跌买**（`step` 价格下行 `_fill_buys_descending`）：对区间内每条空网格线，就近优先
  逐格买入，目标价 = 上一格线价。先 `ensure_covers_down_to` 保证跌破下沿后有延伸买点。
- **涨卖**（`step` 价格上行 `_fill_sells_ascending`）：卖出目标价落在区间内的持仓单元，
  结算已实现盈亏。
- **向上追踪**：涨破当前上沿 → `shift_up_to` 整窗上移；`upper_rebuild_ratio>0` 则按
  比例 `_build_center` 立即重建底仓（0=只上移等回调再买，1=立即全量重建）。
- **资金上限**：`_execute_buy` 里，占用资金 + 本笔成本超过 `capital_cap` 就不成交
  （返回 None），跌得再深也不再新买，兜底黑天鹅。

**内部账本**（供回测 / 报告读取）：`committed`（占用资金）、`realized_pnl`（已实现
盈亏，已扣两边手续费）、`total_fee`、`cash_flow`（净现金流）、`open_positions`（持仓快照）。

**守恒校验**（单测保证）：一轮买卖平仓后，`cash_flow == realized_pnl`。

## ④ 改动历史

- **2026-07-06（M1 首次实现）**：
  - gridlines：等差/等比生成 + 向下放大延伸 + 向上平移，纯函数。
  - ladder：阶梯可变状态，延伸（含金额放大）+ 上移重建。
  - engine：建仓（中枢/零底仓）、跌买涨卖配对、向上追踪 + 按比例重建、向下延伸买入、
    资金硬上限、成交结算与内部账本，另提供 `desired_orders` 供实盘对账。
  - 单测覆盖：单格round-trip精确盈亏、中枢建仓、资金上限、向下放大延伸、上破追踪
    （重建 0 / 1 两种）、desired_orders、守恒。
