"""Parquet 缓存往返测试（tmp_path，不碰网络）。"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.data.cache import ParquetCache


def _bar(
    d: str,
    o: str = "1.00",
    h: str = "1.05",
    lo: str = "0.99",
    c: str = "1.03",
    v: str = "100",
) -> Bar:
    return Bar(
        ts=datetime.fromisoformat(d),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
        volume=Decimal(v),
    )


def test_cache_roundtrip(tmp_path: Path) -> None:
    cache = ParquetCache(tmp_path)
    series = BarSeries(
        symbol="159920",
        frame=Frame.DAILY,
        bars=(_bar("2024-01-02"), _bar("2024-01-03")),
    )
    cache.save(series)
    loaded = cache.load("159920", Frame.DAILY)
    assert loaded == series


def test_cache_missing_returns_none(tmp_path: Path) -> None:
    cache = ParquetCache(tmp_path)
    assert cache.load("159920", Frame.DAILY) is None


def test_cache_decimal_precision_preserved(tmp_path: Path) -> None:
    """价格按 string 存，三位小数无损往返。"""
    cache = ParquetCache(tmp_path)
    series = BarSeries(
        symbol="159920",
        frame=Frame.DAILY,
        bars=(_bar("2024-01-02", o="1.005", h="1.057", lo="0.993", c="1.031"),),
    )
    cache.save(series)
    loaded = cache.load("159920", Frame.DAILY)
    assert loaded is not None
    assert loaded.bars[0].open == Decimal("1.005")
    assert loaded.bars[0].close == Decimal("1.031")


def test_cache_separated_by_frame(tmp_path: Path) -> None:
    """同标的不同周期分别缓存。"""
    cache = ParquetCache(tmp_path)
    daily = BarSeries(symbol="159920", frame=Frame.DAILY, bars=(_bar("2024-01-02"),))
    minute = BarSeries(symbol="159920", frame=Frame.MINUTE, bars=(_bar("2024-01-02T09:31:00"),))
    cache.save(daily)
    cache.save(minute)
    assert cache.load("159920", Frame.DAILY) == daily
    assert cache.load("159920", Frame.MINUTE) == minute
