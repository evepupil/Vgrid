"""金额 / 份额工具测试。"""

from decimal import Decimal

import pytest

from vgrid.core.money import (
    quantize_cash,
    quantize_price,
    shares_for_amount,
)


def test_shares_floor_to_lot() -> None:
    # 2000 / 1.05 = 1904.7 → 1904 → 向下取整到整手 → 1900
    assert shares_for_amount(Decimal("2000"), Decimal("1.05")) == 1900


def test_shares_exact_lot() -> None:
    # 2100 / 1.05 = 2000 刚好整手
    assert shares_for_amount(Decimal("2100"), Decimal("1.05")) == 2000


def test_shares_not_enough_for_one_lot() -> None:
    # 预算连一手都买不起 → 0
    assert shares_for_amount(Decimal("50"), Decimal("1.00")) == 0


def test_shares_rejects_nonpositive_price() -> None:
    with pytest.raises(ValueError, match="价格必须为正"):
        shares_for_amount(Decimal("2000"), Decimal("0"))


def test_quantize_price_to_tick() -> None:
    assert quantize_price(Decimal("1.23456")) == Decimal("1.235")


def test_quantize_cash_to_cent() -> None:
    assert quantize_cash(Decimal("0.099975")) == Decimal("0.10")
