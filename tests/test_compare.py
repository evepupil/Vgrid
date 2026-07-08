"""策略对比测试：三方同起始现金、同口径（纯逻辑）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from vgrid.backtest.compare import compare_strategies
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.dca.config import DcaConfig, Frequency


def _series(rows: list[tuple[date, str, str, str, str]]) -> BarSeries:
    """rows: (日期, open, high, low, close)。"""
    bars = []
    for d, o, h, low, c in rows:
        ts = datetime(d.year, d.month, d.day)
        bars.append(
            Bar(
                ts=ts,
                open=Decimal(o),
                high=Decimal(h),
                low=Decimal(low),
                close=Decimal(c),
                volume=Decimal("1000"),
            )
        )
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=tuple(bars))


def _rising_series(n: int = 60) -> BarSeries:
    """约一年、6 天一根、缓涨（1.00→~1.30），让 XIRR 落在正常范围内。"""
    rows = []
    for i in range(n):
        p = 1.00 + i * 0.005
        s = f"{p:.3f}"
        rows.append((date(2024, 1, 1) + timedelta(days=i * 6), s, s, s, s))
    return _series(rows)


def _grid() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.90"),
        upper_price=Decimal("1.50"),
        grid_count=10,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )


def _dca() -> DcaConfig:
    return DcaConfig(
        symbol="159920",
        frequency=Frequency.DAILY,
        base_amount=Decimal("2000"),
        cash_cap=Decimal("50000"),
    )


def test_three_rows_same_initial_cash() -> None:
    bars = _rising_series()
    cmp = compare_strategies(
        bars, initial_cash=Decimal("50000"), grid_config=_grid(), dca_config=_dca()
    )
    names = [r.name for r in cmp.rows]
    assert names == ["网格", "定投", "买入持有"]
    assert cmp.initial_cash == Decimal("50000")
    # 净利口径统一：profit == final_equity − initial_cash
    for r in cmp.rows:
        assert r.profit == r.final_equity - Decimal("50000")


def test_dca_row_has_invested_and_xirr() -> None:
    bars = _rising_series()
    cmp = compare_strategies(bars, initial_cash=Decimal("50000"), dca_config=_dca())
    dca_row = next(r for r in cmp.rows if r.name == "定投")
    bh_row = next(r for r in cmp.rows if r.name == "买入持有")
    assert dca_row.invested is not None and dca_row.invested > 0
    assert dca_row.xirr is not None  # 涨势里分批买，有解
    assert bh_row.invested is None and bh_row.xirr is None  # 买入持有没有这两项


def test_buy_hold_baseline_always_present() -> None:
    bars = _rising_series()
    cmp = compare_strategies(bars, initial_cash=Decimal("50000"), grid_config=_grid())
    assert [r.name for r in cmp.rows] == ["网格", "买入持有"]  # 只给网格也带出基线


def test_requires_at_least_one_config() -> None:
    bars = _rising_series()
    with pytest.raises(ValueError, match="至少要给"):
        compare_strategies(bars, initial_cash=Decimal("50000"))


def test_empty_bars_raises() -> None:
    empty = BarSeries(symbol="159920", frame=Frame.DAILY, bars=())
    with pytest.raises(ValueError, match="至少需要一根"):
        compare_strategies(empty, initial_cash=Decimal("50000"), dca_config=_dca())
