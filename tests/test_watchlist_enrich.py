"""关注列表增强测试：stub 报价 + stub 历史（临时缓存），验证拼装与按行降级。"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.web.portfolio import WatchItem
from vgrid.web.quotes import Quote
from vgrid.web.watchlist_enrich import WatchlistEnricher

_TODAY = date(2024, 6, 1)


class _StubQuotes:
    def __init__(self, quotes: dict[str, Quote]) -> None:
        self._q = quotes

    def fetch_many(self, symbols: list[str]) -> list[Quote]:
        return [self._q[s] for s in symbols if s in self._q]


class _StubBars:
    """按 symbol 造 70 根日线：'chop' 震荡、'trend' 单边，其余抛错（模拟历史缺失）。"""

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        if symbol == "MISSING":
            raise RuntimeError("no data")
        bars = []
        first = end - timedelta(days=69)  # 70 根日线，末根落在请求 end 上
        for i in range(70):
            px = 1.0 + i * 0.01 if symbol == "TREND" else 1.0 + 0.05 * math.sin(i / 2.0)
            c = Decimal(str(round(px, 4)))
            half = Decimal(str(round(px * 0.02 / 2, 4)))
            bars.append(
                Bar(
                    ts=datetime.combine(first + timedelta(days=i), datetime.min.time()),
                    open=c,
                    high=c + half,
                    low=c - half,
                    close=c,
                    volume=Decimal("100"),
                )
            )
        return BarSeries(symbol=symbol, frame=frame, bars=tuple(bars))


def _item(symbol: str, name: str | None = None) -> WatchItem:
    return WatchItem(symbol=symbol, name=name, added_at=datetime(2024, 5, 1))


def _enricher(tmp_path: Path, quotes: dict[str, Quote]) -> WatchlistEnricher:
    return WatchlistEnricher(
        _StubQuotes(quotes),
        bar_provider=_StubBars(),
        cache_dir=tmp_path,
        today=_TODAY,
    )


def test_enrich_fills_quote_and_fitness(tmp_path: Path) -> None:
    q = Quote("CHOP", "震荡ETF", Decimal("1.05"), Decimal("1.04"), Decimal("0.01"), Decimal("0.96"))
    rows = _enricher(tmp_path, {"CHOP": q}).enrich([_item("CHOP")])
    assert len(rows) == 1
    r = rows[0]
    assert r.price == Decimal("1.05")
    assert r.change_pct == Decimal("0.96")
    assert r.fitness_score is not None and 0 <= r.fitness_score <= 100
    assert r.amplitude_pct is not None
    assert len(r.trend) == 60  # 窗口取最近 60 根
    assert r.error is None


def test_name_falls_back_to_watchitem_when_quote_missing(tmp_path: Path) -> None:
    rows = _enricher(tmp_path, {}).enrich([_item("CHOP", "我的备注名")])
    r = rows[0]
    assert r.name == "我的备注名"
    assert r.price is None and r.change_pct is None
    # 报价缺失但历史仍在：适配分照算
    assert r.fitness_score is not None
    assert len(r.trend) == 60


def test_history_failure_degrades_row(tmp_path: Path) -> None:
    q = Quote("MISSING", "无历史", Decimal("2.0"), None, None, None)
    rows = _enricher(tmp_path, {"MISSING": q}).enrich([_item("MISSING")])
    r = rows[0]
    assert r.price == Decimal("2.0")  # 行情列仍在
    assert r.fitness_score is None  # 派生数据降级
    assert r.trend == []
    assert r.error is not None


def test_chop_scores_higher_than_trend(tmp_path: Path) -> None:
    rows = _enricher(tmp_path, {}).enrich([_item("CHOP"), _item("TREND")])
    chop, trend = rows[0], rows[1]
    assert chop.fitness_score is not None and trend.fitness_score is not None
    assert chop.fitness_score > trend.fitness_score
