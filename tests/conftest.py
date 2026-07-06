"""测试共用夹具。"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest

from vgrid.core import GridConfig

MakeConfig = Callable[..., GridConfig]


@pytest.fixture
def make_config() -> MakeConfig:
    """配置工厂：给一套合理默认，测试按需覆盖单个字段。

    默认区间 1.00~1.20、4 格（等差 step=0.05）、每格 2000 元、资金上限 5 万。
    """

    def _make(**overrides: Any) -> GridConfig:
        params: dict[str, Any] = {
            "symbol": "159920",
            "lower_price": Decimal("1.00"),
            "upper_price": Decimal("1.20"),
            "grid_count": 4,
            "per_grid_amount": Decimal("2000"),
            "capital_cap": Decimal("50000"),
        }
        params.update(overrides)
        return GridConfig(**params)

    return _make
