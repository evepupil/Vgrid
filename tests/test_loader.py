"""load_bars 缓存命中 / 增量合并 / refresh 测试。用 FakeProvider，不打网。"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.data.loader import load_bars


def _bar(d: str) -> Bar:
    return Bar(
        ts=datetime.fromisoformat(d),
        open=Decimal("1.00"),
        high=Decimal("1.01"),
        low=Decimal("0.99"),
        close=Decimal("1.00"),
        volume=Decimal("100"),
    )


class FakeProvider:
    """记下每次 fetch 请求的区间，返回 available 里命中的 K 线。"""

    def __init__(self, available: tuple[Bar, ...]) -> None:
        self._available = available
        self.calls: list[tuple[date, date]] = []

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        self.calls.append((start, end))
        bars = tuple(b for b in self._available if start <= b.ts.date() <= end)
        return BarSeries(symbol=symbol, frame=frame, bars=bars)


def test_fetches_then_caches(tmp_path: Path) -> None:
    prov = FakeProvider((_bar("2024-01-02"), _bar("2024-01-03"), _bar("2024-01-04")))
    bars = load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 4),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(bars) == 3
    assert len(prov.calls) == 1


def test_cache_hit_skips_fetch(tmp_path: Path) -> None:
    prov = FakeProvider((_bar("2024-01-02"), _bar("2024-01-04")))
    load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 4),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    prov.calls.clear()
    bars = load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 4),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(prov.calls) == 0
    assert len(bars) == 2


def test_slice_within_cache(tmp_path: Path) -> None:
    prov = FakeProvider((_bar("2024-01-02"), _bar("2024-01-03"), _bar("2024-01-04")))
    load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 4),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    prov.calls.clear()
    bars = load_bars(
        "159920",
        date(2024, 1, 3),
        date(2024, 1, 3),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(prov.calls) == 0
    assert len(bars) == 1
    assert bars[0].ts.date() == date(2024, 1, 3)


def test_incremental_merge_extends_cache(tmp_path: Path) -> None:
    all_bars = tuple(_bar(f"2024-01-0{i}") for i in range(2, 6))  # 02..05
    prov = FakeProvider(all_bars)
    load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 3),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(prov.calls) == 1
    # 缓存只到 01-03，请求 01-02~05 需要补下
    bars = load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 5),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(prov.calls) == 2
    assert len(bars) == 4


def test_refresh_forces_fetch(tmp_path: Path) -> None:
    prov = FakeProvider((_bar("2024-01-02"), _bar("2024-01-03")))
    load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 3),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    prov.calls.clear()
    load_bars(
        "159920",
        date(2024, 1, 2),
        date(2024, 1, 3),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
        refresh=True,
    )
    assert len(prov.calls) == 1


def test_out_of_range_returns_empty(tmp_path: Path) -> None:
    prov = FakeProvider((_bar("2024-01-02"),))
    bars = load_bars(
        "159920",
        date(2024, 6, 1),
        date(2024, 6, 2),
        Frame.DAILY,
        provider=prov,
        cache_dir=tmp_path,
    )
    assert len(bars) == 0
