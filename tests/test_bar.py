"""K 线 Bar 模型测试。"""

from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame


def _bar(ts: str, o: str, h: str, low: str, c: str, v: str = "100") -> Bar:
    return Bar(
        ts=datetime.fromisoformat(ts),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
        volume=Decimal(v),
    )


def test_bar_accepts_valid_ohlc() -> None:
    b = _bar("2024-01-02", "1.00", "1.05", "0.98", "1.03")
    assert b.close == Decimal("1.03")


def test_bar_allows_equal_high_low() -> None:
    """一字板：high == low 合法。"""
    b = _bar("2024-01-02", "1.00", "1.00", "1.00", "1.00")
    assert b.high == b.low == Decimal("1.00")


def test_bar_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError):
        _bar("2024-01-02", "0", "1.05", "0.98", "1.03")


def test_bar_rejects_high_below_low() -> None:
    with pytest.raises(ValueError):
        _bar("2024-01-02", "1.00", "0.90", "1.05", "1.00")


def test_bar_rejects_close_above_high() -> None:
    with pytest.raises(ValueError):
        _bar("2024-01-02", "1.00", "1.02", "0.99", "1.05")


def test_bar_rejects_negative_volume() -> None:
    with pytest.raises(ValueError):
        _bar("2024-01-02", "1.00", "1.05", "0.98", "1.03", v="-1")


def test_bar_series_empty_ok() -> None:
    bs = BarSeries(symbol="159920", frame=Frame.DAILY)
    assert len(bs) == 0
    assert list(bs) == []


def test_bar_series_requires_strictly_increasing_ts() -> None:
    with pytest.raises(ValueError):
        BarSeries(
            symbol="159920",
            frame=Frame.DAILY,
            bars=(
                _bar("2024-01-03", "1", "1", "1", "1"),
                _bar("2024-01-02", "1", "1", "1", "1"),
            ),
        )


def test_bar_series_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError):
        BarSeries(symbol="", frame=Frame.DAILY, bars=())


def test_bar_series_indexing_and_iter() -> None:
    bars = (
        _bar("2024-01-02", "1.00", "1.02", "0.99", "1.01"),
        _bar("2024-01-03", "1.01", "1.03", "1.00", "1.02"),
    )
    bs = BarSeries(symbol="159920", frame=Frame.MINUTE, bars=bars)
    assert bs[0].close == Decimal("1.01")
    assert [b.open for b in bs] == [Decimal("1.00"), Decimal("1.01")]
    assert len(bs) == 2
