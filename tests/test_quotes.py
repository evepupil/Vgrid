"""报价换算逻辑测试：通达信快照 → Quote，涨跌由现价 / 昨收算（纯函数）。"""

from __future__ import annotations

from decimal import Decimal

from vgrid.data.mootdx_quotes import Snapshot
from vgrid.web.quotes import _snapshot_to_quote


def _snap(price: str, last_close: str | None) -> Snapshot:
    return Snapshot(
        code="159920",
        price=Decimal(price),
        last_close=Decimal(last_close) if last_close is not None else None,
        open=None,
        high=None,
        low=None,
    )


def test_change_from_prev_close() -> None:
    """给现价 + 昨收，涨跌额 / 涨跌幅应被算出。"""
    q = _snapshot_to_quote(_snap("1.10", "1.00"))
    assert q.prev_close == Decimal("1.00")
    assert q.change == Decimal("0.10")
    assert q.change_pct == Decimal("10")


def test_prev_close_missing_leaves_change_none() -> None:
    """昨收缺（通达信没给）：涨跌置空，不硬编。"""
    q = _snapshot_to_quote(_snap("1.10", None))
    assert q.prev_close is None
    assert q.change is None
    assert q.change_pct is None


def test_name_not_provided() -> None:
    """通达信报价无名称字段，Quote.name 留空（名称走 /api/etf/{code}/info）。"""
    q = _snapshot_to_quote(_snap("1.10", "1.00"))
    assert q.name is None
