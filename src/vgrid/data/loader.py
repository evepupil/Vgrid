"""load_bars：组合 provider + cache 的门面。

取数策略：先查缓存；缓存覆盖请求区间就切片返回，否则向 provider 下载请求区间、
与缓存合并去重后覆盖落盘，再切片返回。``refresh=True`` 跳过命中判断，强制下载并合并。

区间框定（covers / slice）按「日」比（用 ``bar.ts.date()`` 与 start/end 的 date 比），
日线 / 分钟线统一适用——分钟线按交易日框区间。去重按完整 ``ts``（datetime），保证
同一天的多个分钟线不会被互相覆盖。

**已知限制（见 review #7）**：``_covers`` 只看缓存里首末两根 K 线的日期能否包住请求
区间，**查不出区间内部的缺日**。一旦某次 fetch 因上游异常 / 代理中断返回了不连续的
序列，这个洞会永久留在缓存里，之后「首末能包住」的请求会被误判命中、返回残缺数据，
回测在不知情下跑在不完整行情上。彻底修需要一份交易日历（按「区间内应有多少交易日 vs
实际根数」校验），暂未接入；`refresh=True` 可强制重新下载绕过缓存。
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.data.cache import ParquetCache
from vgrid.data.mootdx_provider import MootdxProvider
from vgrid.data.provider import BarProvider
from vgrid.data.tencent_provider import TencentProvider


def default_cache_dir() -> Path:
    """默认缓存目录：``~/.vgrid/cache``（用户目录，不污染 repo）。"""
    return Path.home() / ".vgrid" / "cache"


def _default_provider(frame: Frame, adjust: str) -> BarProvider:
    """按周期选默认源：日线走腾讯（按 ``adjust`` 复权），分钟走 mootdx（通达信，恒不复权）。

    东财 / 新浪源已弃用（em 海外不通、sina 不复权），现只留这两个稳定源。
    ``adjust`` 只对日线有意义：回测要前复权（qfq），红利收益对比要不复权（""）。
    """
    if frame is Frame.DAILY:
        return TencentProvider(adjust=adjust)
    return MootdxProvider()  # 1m / 5m 分钟线（mootdx 只出不复权，忽略 adjust）


def load_bars(
    symbol: str,
    start: date,
    end: date,
    frame: Frame,
    *,
    provider: BarProvider | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    adjust: str = "qfq",
) -> BarSeries:
    """取 [start, end] 闭区间 K 线，优先缓存，缺了才下载并增量合并落盘。

    ``adjust`` 选复权方式（默认前复权），前复权与不复权缓存分文件互不覆盖。
    """
    cache = ParquetCache(cache_dir or default_cache_dir())
    prov = provider or _default_provider(frame, adjust)

    cached = _load_cached(cache, symbol, frame, adjust)
    if not refresh and _covers(cached, start, end):
        return _series(symbol, frame, _slice(cached, start, end))

    fresh = prov.fetch(symbol, start, end, frame)
    merged = _merge(cached, fresh.bars)
    if merged:
        cache.save(_series(symbol, frame, merged), adjust)
    return _series(symbol, frame, _slice(merged, start, end))


def _load_cached(
    cache: ParquetCache, symbol: str, frame: Frame, adjust: str,
) -> tuple[Bar, ...]:
    series = cache.load(symbol, frame, adjust)
    return series.bars if series is not None else ()


def _series(symbol: str, frame: Frame, bars: tuple[Bar, ...]) -> BarSeries:
    return BarSeries(symbol=symbol, frame=frame, bars=bars)


def _covers(bars: tuple[Bar, ...], start: date, end: date) -> bool:
    """bars 是否覆盖 [start, end]（只按首末日期判断）。

    注意：只保证首末日期包住区间，**不保证中间无缺失**。详见模块 docstring 的
    「已知限制（review #7）」。
    """
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
