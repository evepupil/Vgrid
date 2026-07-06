"""手续费模型测试。"""

from decimal import Decimal

import pytest

from vgrid.core import FeeModel


def test_rate_applies_above_floor() -> None:
    fee = FeeModel()
    # 10 万成交额 × 万0.5 = 5 元，高于 0.1 起收
    assert fee.compute(Decimal("100000")) == Decimal("5")


def test_min_floor_applies_for_small_notional() -> None:
    fee = FeeModel()
    # 1000 元 × 万0.5 = 0.05，被 0.1 起收拉高
    assert fee.compute(Decimal("1000")) == Decimal("0.1")


def test_min_efficient_notional_is_2000() -> None:
    # 0.1 / 0.00005 = 2000：低于这个成交额，实际费率就高于名义费率
    assert FeeModel().min_efficient_notional == Decimal("2000")


def test_negative_notional_rejected() -> None:
    with pytest.raises(ValueError, match="成交额不能为负"):
        FeeModel().compute(Decimal("-1"))


def test_negative_rate_rejected() -> None:
    with pytest.raises(ValueError, match="费率不能为负"):
        FeeModel(rate=Decimal("-0.001"))
