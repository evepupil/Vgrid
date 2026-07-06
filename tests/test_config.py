"""网格配置校验测试。"""

from collections.abc import Callable
from decimal import Decimal

import pytest

from vgrid.core import GridConfig

MakeConfig = Callable[..., GridConfig]


def test_valid_config(make_config: MakeConfig) -> None:
    cfg = make_config()
    assert cfg.symbol == "159920"
    assert cfg.is_amount_fee_efficient  # 每格 2000 达到费率临界


def test_amount_below_efficient_threshold(make_config: MakeConfig) -> None:
    cfg = make_config(per_grid_amount=Decimal("1500"))
    assert not cfg.is_amount_fee_efficient


def test_upper_must_exceed_lower(make_config: MakeConfig) -> None:
    with pytest.raises(ValueError, match="必须大于下沿"):
        make_config(lower_price=Decimal("1.2"), upper_price=Decimal("1.0"))


def test_grid_count_at_least_one(make_config: MakeConfig) -> None:
    with pytest.raises(ValueError, match="格数至少为 1"):
        make_config(grid_count=0)


def test_rebuild_ratio_in_range(make_config: MakeConfig) -> None:
    with pytest.raises(ValueError, match="库存重建比例"):
        make_config(upper_rebuild_ratio=Decimal("1.5"))


def test_down_spacing_factor_at_least_one(make_config: MakeConfig) -> None:
    with pytest.raises(ValueError, match="向下格距放大系数"):
        make_config(down_spacing_factor=Decimal("0.9"))


def test_capital_cap_positive(make_config: MakeConfig) -> None:
    with pytest.raises(ValueError, match="资金上限必须为正"):
        make_config(capital_cap=Decimal("0"))
