"""网格阶梯的结构化视图（供前端画工程图）。

从引擎**当前状态**派生一份只读快照：每条网格线归类成
卖单格 / 买单格 / 排队格（超资金上限）/ 空闲，并标出资金上限触及价、现价、
以及每条线属于基准窗口还是向下放大区（``depth``）。

**复用引擎自己的 ``desired_orders`` 口径**做买单分类——画出来的阶梯与引擎真实
会挂的限价单一致，不在这里另写一套分类逻辑，免得两处实现分叉。纯函数、不改状态。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from vgrid.core.enums import Side
from vgrid.strategy.engine import GridEngine

# 网格线归类
KIND_SELL = "sell"  # 持有底仓、挂卖单等止盈（红涨绿跌里显绿）
KIND_BUY = "buy"  # 现价下方、资金上限内的在挂买单（显红）
KIND_CAPPED = "capped"  # 现价下方但被资金上限挡下的排队买单（虚线）
KIND_IDLE = "idle"  # 无单无持仓的空闲线（现价上方无底仓 / 上一格已持有）


@dataclass(frozen=True, slots=True)
class LadderRung:
    """一条网格线在当前状态下的展示信息。"""

    price: Decimal
    depth: int  # 0=基准窗口，k>0=基准下沿之下第 k 层放大区
    kind: str  # KIND_* 之一
    held_shares: int  # kind==sell 时为持有份额，其余为 0


@dataclass(frozen=True, slots=True)
class LadderView:
    """整条阶梯的结构化视图。"""

    rungs: list[LadderRung]  # 从低到高
    current_price: Decimal
    cap_price: Decimal | None  # 资金上限触及价（最高一条排队格），无排队格则 None
    window_lower: Decimal  # 基准窗口下沿
    window_upper: Decimal  # 基准窗口上沿
    step: Decimal  # 基准窗口底部格距
    grid_count: int
    spacing_mode: str


def build_ladder_view(engine: GridEngine, price: Decimal) -> LadderView:
    """从引擎当前状态 + 现价，构造结构化阶梯视图。

    分类口径：
    - 有持仓单元卖在这条线上 → 卖单格（带份额）。
    - 现价上方、无持仓 → 空闲。
    - 现价下方、在 ``desired_orders`` 的买单里 → 买单格。
    - 现价下方、上一格已持有（引擎不重复买）→ 空闲。
    - 现价下方、其余（被资金上限挡下）→ 排队格；最高的一条即资金上限触及价。
    """
    lines = engine.ladder.lines  # 低→高
    lots_by_target = {lot.sell_target: lot for lot in engine.open_positions}
    buy_prices = {o.price for o in engine.desired_orders(price) if o.side is Side.BUY}

    base_prices = [ln.price for ln in lines if ln.depth == 0]
    window_lower = min(base_prices)
    window_upper = max(base_prices)
    step = base_prices[1] - base_prices[0] if len(base_prices) >= 2 else Decimal(0)  # noqa: PLR2004

    rungs: list[LadderRung] = []
    cap_price: Decimal | None = None
    for ln in lines:
        p = ln.price
        lot = lots_by_target.get(p)
        if lot is not None:
            rungs.append(LadderRung(p, ln.depth, KIND_SELL, lot.shares))
        elif p >= price:
            rungs.append(LadderRung(p, ln.depth, KIND_IDLE, 0))
        elif p in buy_prices:
            rungs.append(LadderRung(p, ln.depth, KIND_BUY, 0))
        else:
            above = engine.ladder.line_above(p)
            if above is not None and above.price in lots_by_target:
                # 上一格已持有，引擎不会在这买 → 空闲，不是被上限挡下
                rungs.append(LadderRung(p, ln.depth, KIND_IDLE, 0))
            else:
                rungs.append(LadderRung(p, ln.depth, KIND_CAPPED, 0))
                if cap_price is None or p > cap_price:
                    cap_price = p

    return LadderView(
        rungs=rungs,
        current_price=price,
        cap_price=cap_price,
        window_lower=window_lower,
        window_upper=window_upper,
        step=step,
        grid_count=engine.config.grid_count,
        spacing_mode=engine.config.spacing_mode.value,
    )
