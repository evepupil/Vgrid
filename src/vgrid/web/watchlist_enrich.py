"""关注列表增强：给每个自选标的补实时行情 + 振幅 + 网格适配评分 + 近 N 日走势（FR-10.2~10.4）。

关注列表本体（CRUD）在 ``PortfolioManager``；这里只做「读一批 symbol → 拼派生数据」。
两个数据源都可注入（``QuoteProvider`` 实时报价、``BarProvider`` 历史日线），离线 / 测试
换 stub。**任一源失败都按行降级**：报价挂了行情列留空、历史挂了适配分/走势留空，但整表
照返，不让关注页崩——和 ``/api/quotes`` 同样的「实时性让位于稳定性」。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from vgrid.analysis import grid_fitness
from vgrid.core.bar import Bar
from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.data.provider import BarProvider
from vgrid.web.portfolio import WatchItem
from vgrid.web.quotes import Quote, QuoteProvider

_WINDOW = 60  # 走势 / 评分取最近这么多根日线
_LOOKBACK_DAYS = 90  # 往前多要些自然日，凑够 ~60 个交易日


@dataclass(frozen=True, slots=True)
class EnrichedWatch:
    """一条关注 + 派生数据。行情 / 历史缺失的字段为 ``None``（前端降级显示）。"""

    symbol: str
    name: str | None
    added_at: datetime
    price: Decimal | None
    change_pct: Decimal | None
    amplitude_pct: Decimal | None
    fitness_score: int | None
    trendiness: Decimal | None
    crossings: int | None
    trend: list[Decimal]  # 近 N 日收盘，供 sparkline（空则前端不画）
    error: str | None


class WatchlistEnricher:
    """把关注项批量拼上实时行情 + 网格适配评分。"""

    def __init__(
        self,
        quote_provider: QuoteProvider,
        *,
        bar_provider: BarProvider | None = None,
        cache_dir: Path | None = None,
        window: int = _WINDOW,
        lookback_days: int = _LOOKBACK_DAYS,
        today: date | None = None,
    ) -> None:
        self._quotes = quote_provider
        self._bars = bar_provider
        self._cache_dir = cache_dir
        self._window = window
        self._lookback_days = lookback_days
        self._today = today

    def enrich(self, items: list[WatchItem]) -> list[EnrichedWatch]:
        quotes = self._fetch_quotes([it.symbol for it in items])
        return [self._one(it, quotes.get(it.symbol)) for it in items]

    def _fetch_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        if not symbols:
            return {}
        try:
            return {q.symbol: q for q in self._quotes.fetch_many(symbols)}
        except Exception:  # 报价源挂了：行情列留空，适配分/走势仍可算
            return {}

    def _one(self, item: WatchItem, quote: Quote | None) -> EnrichedWatch:
        amplitude: Decimal | None = None
        score: int | None = None
        trendiness: Decimal | None = None
        crossings: int | None = None
        trend: list[Decimal] = []
        error: str | None = None
        try:
            window_bars = self._load_window(item.symbol)
            trend = [b.close for b in window_bars]
            gf = grid_fitness(window_bars)
            if gf is not None:
                amplitude, score = gf.amplitude_pct, gf.score
                trendiness, crossings = gf.trendiness, gf.crossings
        except Exception as exc:  # 历史行情任一环节失败：只丢派生数据，不丢整行
            error = f"历史行情不可用：{exc}"
        return EnrichedWatch(
            symbol=item.symbol,
            name=quote.name if quote and quote.name else item.name,
            added_at=item.added_at,
            price=quote.price if quote else None,
            change_pct=quote.change_pct if quote else None,
            amplitude_pct=amplitude,
            fitness_score=score,
            trendiness=trendiness,
            crossings=crossings,
            trend=trend,
            error=error,
        )

    def _load_window(self, symbol: str) -> list[Bar]:
        end = self._today or date.today()
        start = end - timedelta(days=self._lookback_days)
        series = load_bars(
            symbol,
            start,
            end,
            Frame.DAILY,
            provider=self._bars,
            cache_dir=self._cache_dir,
        )
        return list(series.bars)[-self._window :]


def enriched_to_dict(e: EnrichedWatch) -> dict[str, object]:
    """EnrichedWatch → JSON 安全 dict（Decimal→str，None 透传）。"""
    return {
        "symbol": e.symbol,
        "name": e.name,
        "added_at": e.added_at.isoformat(),
        "price": str(e.price) if e.price is not None else None,
        "change_pct": str(e.change_pct) if e.change_pct is not None else None,
        "amplitude_pct": str(e.amplitude_pct) if e.amplitude_pct is not None else None,
        "fitness_score": e.fitness_score,
        "trendiness": str(e.trendiness) if e.trendiness is not None else None,
        "crossings": e.crossings,
        "trend": [str(c) for c in e.trend],
        "error": e.error,
    }
