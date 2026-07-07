"""读 SQLite → replay engine → 算面板状态（纯逻辑，单测重点）。

不长驻 engine（那是 ``paper run`` 的事）。每次 ``load_state`` 读全部 tick / fill / config，
replay ``GridEngine`` 逐 tick 算权益曲线，复用 ``backtest.metrics`` 的回撤 / 夏普，曲线降采样
到 N 点并标记成交点。

夏普按「日折算」近似（tick 频率高时会偏低，看盘参考用，不是严谨绩效）。
"""

from __future__ import annotations

import sqlite3
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from vgrid.backtest.metrics import max_drawdown_of, sharpe_of
from vgrid.backtest.result import EquityPoint
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame, Side
from vgrid.core.models import Fill
from vgrid.core.money import shares_for_amount
from vgrid.store.repository import load_config, load_fills, load_ticks
from vgrid.strategy.engine import GridEngine
from vgrid.strategy.ladder_view import LadderView, build_ladder_view
from vgrid.web.curve import downsample


@dataclass(frozen=True, slots=True)
class FillMark:
    """成交点在降采样曲线上的位置（供前端 SVG 标注）。"""

    index: int
    side: Side
    price: Decimal
    shares: int
    realized_pnl: Decimal | None


@dataclass(frozen=True, slots=True)
class StateView:
    """面板状态快照。"""

    symbol: str
    config: dict[str, object]
    snapshot: dict[str, object]
    metrics: dict[str, object]
    fills: list[Fill]
    equity_curve: list[EquityPoint]
    drawdown_curve: list[tuple[datetime, Decimal]]  # 逐点回撤比例（<=0），与 equity_curve 同点
    buy_hold_curve: list[tuple[datetime, Decimal]]  # 同笔资金买入持有的逐点权益，同点
    fill_marks: list[FillMark]
    n_ticks: int
    ladder: LadderView | None


def load_state(conn: sqlite3.Connection, *, curve_points: int = 300) -> StateView | None:
    """读库 replay 算面板状态。无 config 返回 None（前端提示无数据）。"""
    config = load_config(conn)
    if config is None:
        return None
    ticks = load_ticks(conn)
    fills = load_fills(conn)
    initial = config.capital_cap

    engine = GridEngine(config)
    full_curve: list[EquityPoint] = []
    marks_raw: list[tuple[int, Fill]] = []
    started = False
    for i, (ts, price) in enumerate(ticks):
        step = engine.start(price) if not started else engine.step(price)
        started = True
        pos_value = Decimal(engine.position.shares) * price
        cash = initial + engine.cash_flow
        full_curve.append(
            EquityPoint(ts=ts, cash=cash, position_value=pos_value, equity=cash + pos_value)
        )
        for f in step:
            marks_raw.append((i, f))

    full_tuple = tuple(full_curve)
    if full_tuple:
        total_return = _ratio(full_tuple[-1].equity - initial, initial)
        max_dd = max_drawdown_of(full_tuple)
        sharpe = sharpe_of(full_tuple, Frame.DAILY)
    else:
        total_return = Decimal(0)
        max_dd = Decimal(0)
        sharpe = Decimal(0)
    buy_hold = _buy_hold(ticks, initial, config)

    sampled, indices = downsample(full_curve, curve_points)
    # 回撤 / 买入持有序列：在全量曲线上算，再按降采样索引对齐到 equity_curve 的点
    dd_full = _drawdown_series(full_curve)
    bh_full = _buy_hold_series(ticks, initial, config)
    drawdown_curve = [(full_curve[i].ts, dd_full[i]) for i in indices]
    buy_hold_curve = [(full_curve[i].ts, bh_full[i]) for i in indices]
    fill_marks = [
        FillMark(
            index=_map_to_sampled(tick_idx, indices),
            side=f.side,
            price=f.price,
            shares=f.shares,
            realized_pnl=f.realized_pnl,
        )
        for tick_idx, f in marks_raw
    ]

    # 浮动盈亏：持仓按现价 mark-to-market − 成本（含买入费）。与已实现分开返回，
    # 是全系统诚实性底线——不许把两者揉成一个「总收益」。
    last_price = ticks[-1][1] if ticks else None
    pos = engine.position
    if last_price is not None and pos.shares > 0:
        position_value = Decimal(pos.shares) * last_price
        unrealized_pnl = position_value - pos.cost
    else:
        position_value = Decimal(0)
        unrealized_pnl = Decimal(0)

    snapshot: dict[str, object] = {
        "last_price": last_price,
        "last_ts": ticks[-1][0] if ticks else None,
        "open_lots": engine.open_lots,
        "committed": engine.committed,
        "realized_pnl": engine.realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "position_shares": pos.shares,
        "position_value": position_value,
        "avg_cost": pos.avg_cost,
        "total_fee": engine.total_fee,
        "cash_flow": engine.cash_flow,
        "n_fills": len(fills),
    }
    # replay 后的 engine 停在当前实时状态，直接抽出带真实持仓的阶梯
    ladder = build_ladder_view(engine, last_price) if last_price is not None else None

    return StateView(
        symbol=config.symbol,
        config=_config_summary(config),
        snapshot=snapshot,
        metrics={
            "total_return": total_return,
            "max_drawdown": max_dd,
            "sharpe": sharpe,
            "buy_hold_return": buy_hold,
        },
        fills=list(fills),
        equity_curve=sampled,
        drawdown_curve=drawdown_curve,
        buy_hold_curve=buy_hold_curve,
        fill_marks=fill_marks,
        n_ticks=len(ticks),
        ladder=ladder,
    )


def _ratio(numer: Decimal, denom: Decimal) -> Decimal:
    if denom == 0:
        return Decimal(0)
    return numer / denom


def _drawdown_series(curve: list[EquityPoint]) -> list[Decimal]:
    """逐点回撤比例：``(权益 − 迄今峰值) / 峰值``，均 ≤ 0。最小值即最大回撤。"""
    out: list[Decimal] = []
    peak = Decimal(0)
    for p in curve:
        peak = max(peak, p.equity)
        out.append((p.equity - peak) / peak if peak > 0 else Decimal(0))
    return out


def _buy_hold_series(
    ticks: list[tuple[datetime, Decimal]], initial: Decimal, config: GridConfig
) -> list[Decimal]:
    """同笔资金首 tick 按手取整建仓后，逐 tick mark-to-market 的权益序列。

    与网格净值同口径：持仓按当时价估值、不扣卖出费（卖出费只在真实平仓时结算），
    两条曲线才能公平对照。买不起一手则全程持币不变。
    """
    if not ticks or initial <= 0:
        return [initial for _ in ticks]
    entry = ticks[0][1]
    shares = shares_for_amount(initial, entry, config.lot_size)
    if shares <= 0:
        return [initial for _ in ticks]
    buy_notional = entry * shares
    leftover = initial - (buy_notional + config.fee.compute(buy_notional))
    return [leftover + price * shares for _, price in ticks]


def _buy_hold(
    ticks: list[tuple[datetime, Decimal]], initial: Decimal, config: GridConfig
) -> Decimal:
    """首 tick 价按手取整买入、末 tick 价卖出的收益率（扣两边手续费）。"""
    if not ticks or initial <= 0:
        return Decimal(0)
    entry = ticks[0][1]
    shares = shares_for_amount(initial, entry, config.lot_size)
    if shares <= 0:
        return Decimal(0)
    buy_notional = entry * shares
    cost = buy_notional + config.fee.compute(buy_notional)
    exit_notional = ticks[-1][1] * shares
    proceeds = exit_notional - config.fee.compute(exit_notional)
    return _ratio(proceeds - cost, cost)


def _map_to_sampled(tick_idx: int, indices: list[int]) -> int:
    """原 tick 索引 → 不超过它的最大采样点位置。"""
    if not indices:
        return 0
    return max(bisect_right(indices, tick_idx) - 1, 0)


def _config_summary(config: GridConfig) -> dict[str, object]:
    return {
        "symbol": config.symbol,
        "lower_price": str(config.lower_price),
        "upper_price": str(config.upper_price),
        "grid_count": config.grid_count,
        "spacing_mode": config.spacing_mode.value,
        "base_build_mode": config.base_build_mode.value,
        "capital_cap": str(config.capital_cap),
        "per_grid_amount": str(config.per_grid_amount),
    }
