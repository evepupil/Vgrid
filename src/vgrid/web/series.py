"""权益曲线派生序列：逐点回撤 + 买入持有对照。看盘(state)与回测(backtest_api)共用。

回撤序列是纯口径复用；买入持有对照按「同笔资金首点建仓、逐点 mark-to-market、不扣卖出费」
算，和网格净值同口径，两条线才能公平对照（见 review #10）。
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import Bar
from vgrid.core.config import GridConfig
from vgrid.core.money import shares_for_amount


def drawdown_series(curve: Sequence[EquityPoint]) -> list[Decimal]:
    """逐点回撤比例：``(权益 − 迄今峰值) / 峰值``，均 ≤ 0。最小值即最大回撤。"""
    out: list[Decimal] = []
    peak = Decimal(0)
    for p in curve:
        peak = max(peak, p.equity)
        out.append((p.equity - peak) / peak if peak > 0 else Decimal(0))
    return out


def buy_hold_series_from_bars(
    bars: Sequence[Bar], initial: Decimal, config: GridConfig
) -> list[Decimal]:
    """回测口径的买入持有逐点权益：首根 ``open`` 按手取整建仓，逐根按 ``close`` 估值。

    与 ``metrics._buy_hold`` 的分母口径一致（零头算作闲置资金）；不扣卖出费——卖出费
    只在真实平仓结算，曲线对照阶段两条线都不扣，才公平。买不起一手则全程持币不变。
    """
    if not bars or initial <= 0:
        return [initial for _ in bars]
    entry = bars[0].open
    shares = shares_for_amount(initial, entry, config.lot_size)
    if shares <= 0:
        return [initial for _ in bars]
    buy_notional = entry * shares
    leftover = initial - (buy_notional + config.fee.compute(buy_notional))
    return [leftover + bar.close * shares for bar in bars]
