"""load_bars：组合 provider + cache 的门面。

取数策略：先查缓存；缓存覆盖请求区间就切片返回，否则向 provider 下载请求区间、
与缓存合并去重后覆盖落盘，再切片返回。``refresh=True`` 跳过命中判断，强制下载并合并。

区间框定（covers / slice）按「日」比（用 ``bar.ts.date()`` 与 start/end 的 date 比），
日线 / 分钟线统一适用——分钟线按交易日框区间。去重按完整 ``ts``（datetime），保证
同一天的多个分钟线不会被互相覆盖。
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.data.akshare_provider import AkshareProvider
from vgrid.data.cache import ParquetCache
from vgrid.data.provider import BarProvider


def default_cache_dir() -> Path:
    """默认缓存目录：``~/.vgrid/cache``（用户目录，不污染 repo）。"""
    return Path.home() / ".vgrid" / "cache"


def load_bars(
    symbol: str,
    start: date,
    end: date,
    frame: Frame,
    *,
    provider: BarProvider | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
) -> BarSeries:
    """取 [start, end] 闭区间 K 线，优先缓存，缺了才下载并增量合并落盘。"""
    cache = ParquetCache(cache_dir or default_cache_dir())
    prov = provider or AkshareProvider()

    cached = _load_cached(cache, symbol, frame)
    if not refresh and _covers(cached, start, end):
        return _series(symbol, frame, _slice(cached, start, end))

    fresh = prov.fetch(symbol, start, end, frame)
    merged = _merge(cached, fresh.bars)
    if merged:
        cache.save(_series(symbol, frame, merged))
    return _series(symbol, frame, _slice(merged, start, end))


def _load_cached(cache: ParquetCache, symbol: str, frame: Frame) -> tuple[Bar, ...]:
    series = cache.load(symbol, frame)
    return series.bars if series is not None else ()


def _series(symbol: str, frame: Frame, bars: tuple[Bar, ...]) -> BarSeries:
    return BarSeries(symbol=symbol, frame=frame, bars=bars)


def _covers(bars: tuple[Bar, ...], start: date, end: date) -> bool:
    """bars 是否完全覆盖 [start, end]（按日比）。"""
    if not bars:
        return False
    return bars[0].ts.date() <= start and bars[-1].ts.date() >= end


def _slice(bars: tuple[Bar, ...], start: date, end: date) -> tuple[Bar, ...]:
    """取日期落在 [start, end] 内的 bars，保持顺序。"""
    return tuple(b for b in bars if start <= b.ts.date() <= end)


def _merge(existing: tuple[Bar, ...], incoming: tuple[Bar, ...]) -> tuple[Bar, ...]:
    """合并两组 Bar，按 ts 去重（incoming 覆盖 existing），按 ts 升序。"""
    by_ts: dict[datetime, Bar] = {b.ts: b for b in existing}
    for bar in incoming:
        by_ts[bar.ts] = bar
    return tuple(sorted(by_ts.values(), key=lambda b: b.ts))
