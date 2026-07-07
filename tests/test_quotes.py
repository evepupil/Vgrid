"""报价补齐逻辑测试：昨收 / 涨跌额 / 涨跌幅 互相补齐（纯函数）。"""

from __future__ import annotations

from decimal import Decimal

from vgrid.web.quotes import _row_to_quote


def test_backfill_change_from_prev_close() -> None:
    """给现价 + 昨收，涨跌额 / 涨跌幅 应被算出。"""
    q = _row_to_quote("159920", {"名称": "恒生 ETF", "最新价": "1.10", "昨收": "1.00"})
    assert q.change == Decimal("0.10")
    assert q.change_pct == Decimal("10")


def test_backfill_prev_close_from_pct() -> None:
    """昨收缺、给涨跌幅，昨收应由 现价 / (1+涨跌幅%) 反推。"""
    q = _row_to_quote("159920", {"最新价": "1.10", "涨跌幅": "10"})
    assert q.prev_close is not None
    assert q.prev_close == Decimal("1.10") / Decimal("1.1")  # = 1.00


def test_missing_price_is_zero() -> None:
    q = _row_to_quote("159920", {"名称": "x"})
    assert q.price == Decimal(0)
