"""限价单撮合：把 BarSeries 喂给 GridEngine，产出 BacktestResult。

回测器只是 M1 引擎的一个驱动器，**策略逻辑一行不改**。撮合假设：每根 K 线按
``先 low 后 high`` 两个价位喂给 ``engine.step``——日内先探底（触发下方买单）再反弹
（触发上方卖单）。建仓用首根 ``open``（不偷看未来）。

每根 K 线收盘记一笔权益：``权益 = 初始资金 + 累计净现金流 + 持仓按收盘价估值``。
平仓后 ``持仓估值 = 0``，此时 ``权益 − 初始资金 == 引擎 realized_pnl``（守恒）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from vgrid.backtest.metrics import compute_metrics
from vgrid.backtest.result import BacktestResult, EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.models import Fill
from vgrid.strategy.engine import GridEngine


def simulate(
    config: GridConfig,
    bars: BarSeries,
    *,
    initial_cash: Decimal | None = None,
) -> BacktestResult:
    """对 ``bars`` 跑网格回测，返回成交、逐 K 权益曲线、绩效指标。"""
    if not bars.bars:
        raise ValueError("至少需要一根 K 线才能回测")

    engine = GridEngine(config)
    cash = initial_cash if initial_cash is not None else config.capital_cap
    fills: list[Fill] = []

    first = bars[0]
    fills.extend(_stamp(engine.start(first.open), first.ts))

    equity_curve: list[EquityPoint] = []
    for bar in bars:
        for price in (bar.low, bar.high):
            fills.extend(_stamp(engine.step(price), bar.ts))
        pos_value = Decimal(engine.position.shares) * bar.close
        cash_now = cash + engine.cash_flow
        equity_curve.append(
            EquityPoint(
                ts=bar.ts,
                cash=cash_now,
                position_value=pos_value,
                equity=cash_now + pos_value,
            )
        )

    metrics = compute_metrics(
        tuple(equity_curve),
        tuple(fills),
        bars.bars,
        initial_cash=cash,
        config=config,
        frame=bars.frame,
    )
    return BacktestResult(
        fills=tuple(fills),
        equity_curve=tuple(equity_curve),
        bars=bars.bars,
        metrics=metrics,
    )


def _stamp(fills: list[Fill], ts: datetime) -> list[Fill]:
    """给引擎产出的成交（默认 ts=None）打上时间戳。"""
    return [replace(f, ts=ts) for f in fills]
