"""回测撮合测试。"""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.backtest import simulate
from vgrid.core import GridConfig
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import BaseBuildMode, Frame, Side

MakeConfig = Callable[..., GridConfig]


def _bar(d: str, o: str, h: str, lo: str, c: str) -> Bar:
    return Bar(
        ts=datetime.fromisoformat(d),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
        volume=Decimal("100"),
    )


def _series(*bars: Bar) -> BarSeries:
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=bars)


def _zero_config() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def test_simulate_rejects_empty() -> None:
    with pytest.raises(ValueError, match="至少需要一根"):
        simulate(_zero_config(), _series())


def test_fills_carry_timestamp_and_round_trip() -> None:
    """买在 01-03 的 low、卖在 01-04 的 high；成交 ts 等于触发它的那根 K 线。"""
    cfg = _zero_config()
    bars = _series(
        _bar("2024-01-02", "1.10", "1.10", "1.10", "1.10"),  # 起步，无成交
        _bar("2024-01-03", "1.06", "1.06", "1.05", "1.05"),  # low=1.05 触发买 @1.05
        _bar("2024-01-04", "1.06", "1.15", "1.06", "1.15"),  # high=1.15 触发卖 @1.10
    )
    result = simulate(cfg, bars)
    buys = [f for f in result.fills if f.side is Side.BUY]
    sells = [f for f in result.fills if f.side is Side.SELL]

    assert len(buys) == 1
    assert buys[0].price == Decimal("1.050")
    assert buys[0].ts == datetime(2024, 1, 3)
    assert len(sells) == 1
    assert sells[0].price == Decimal("1.100")
    assert sells[0].ts == datetime(2024, 1, 4)
    assert sells[0].realized_pnl is not None
    assert sells[0].realized_pnl > 0


def test_equity_curve_length_matches_bars() -> None:
    cfg = _zero_config()
    bars = _series(
        _bar("2024-01-02", "1.10", "1.10", "1.10", "1.10"),
        _bar("2024-01-03", "1.06", "1.06", "1.05", "1.05"),
    )
    result = simulate(cfg, bars)
    assert len(result.equity_curve) == 2
    for pt, bar in zip(result.equity_curve, bars, strict=True):
        assert pt.ts == bar.ts


def test_conservation_after_flat() -> None:
    """全平仓后：权益 − 初始资金 == 累计卖出已实现盈亏（守恒）。"""
    cfg = _zero_config()
    bars = _series(
        _bar("2024-01-02", "1.10", "1.10", "1.10", "1.10"),
        _bar("2024-01-03", "1.06", "1.06", "1.05", "1.05"),
        _bar("2024-01-04", "1.06", "1.15", "1.06", "1.15"),
    )
    result = simulate(cfg, bars)
    final = result.equity_curve[-1]
    assert final.position_value == Decimal(0)  # 末根收盘已平仓

    total_pnl = sum(
        (f.realized_pnl for f in result.fills if f.realized_pnl is not None),
        Decimal(0),
    )
    assert final.equity - result.metrics.initial_cash == total_pnl


def test_default_initial_cash_is_capital_cap() -> None:
    cfg = _zero_config()
    bars = _series(_bar("2024-01-02", "1.10", "1.10", "1.10", "1.10"))
    result = simulate(cfg, bars)
    assert result.metrics.initial_cash == cfg.capital_cap
