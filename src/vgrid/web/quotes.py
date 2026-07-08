"""实时报价：批量取多标的现价 + 昨收 + 涨跌（FR-11.1 / 11.4）。

``QuoteProvider`` 是协议，``MootdxSpotProvider`` 是通达信实现——走 ``data.mootdx_quotes``
的共享连接批量取现价 / 昨收，昨收缺则涨跌置空。取不到的标的跳过，整体失败由调用方降级。

后端只回原始数值 + 昨收，红涨绿跌的颜色由前端定（见需求原则 4）。名称不在报价里给
（通达信报价无名称字段），由 ``/api/etf/{code}/info`` 单独查，前端 ticker 缺名回落代码。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from vgrid.data.mootdx_quotes import MootdxQuotes, Snapshot


@dataclass(frozen=True, slots=True)
class Quote:
    """一个标的的实时报价。"""

    symbol: str
    name: str | None
    price: Decimal
    prev_close: Decimal | None  # 昨收
    change: Decimal | None  # 涨跌额
    change_pct: Decimal | None  # 涨跌幅（%）


@runtime_checkable
class QuoteProvider(Protocol):
    """批量实时报价。"""

    def fetch_many(self, symbols: list[str]) -> list[Quote]: ...


class MootdxSpotProvider:
    """通达信实时报价，按代码批量提取（连接复用）。"""

    def __init__(self) -> None:
        self._quotes = MootdxQuotes()

    def fetch_many(self, symbols: list[str]) -> list[Quote]:
        return [_snapshot_to_quote(s) for s in self._quotes.snapshot(symbols)]


def _snapshot_to_quote(s: Snapshot) -> Quote:
    """通达信快照 → Quote，涨跌由现价 / 昨收算（昨收缺则置空）。"""
    prev = s.last_close
    change = None if prev is None else s.price - prev
    change_pct = None if prev is None or prev == 0 else (s.price - prev) / prev * Decimal(100)
    return Quote(
        symbol=s.code,
        name=None,
        price=s.price,
        prev_close=prev,
        change=change,
        change_pct=change_pct,
    )


def quote_to_dict(q: Quote) -> dict[str, object]:
    """Quote → JSON 安全 dict（Decimal 转 str 保精度）。"""
    return {
        "symbol": q.symbol,
        "name": q.name,
        "price": str(q.price),
        "prev_close": str(q.prev_close) if q.prev_close is not None else None,
        "change": str(q.change) if q.change is not None else None,
        "change_pct": str(q.change_pct) if q.change_pct is not None else None,
    }
