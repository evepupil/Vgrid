"""网格线生成测试。"""

from decimal import Decimal

import pytest

from vgrid.core.enums import SpacingMode
from vgrid.strategy.gridlines import (
    bottom_gap,
    build_levels,
    extend_levels_down,
    shift_window_up,
)


def test_arithmetic_levels() -> None:
    levels = build_levels(Decimal("1.00"), Decimal("1.20"), 4, SpacingMode.ARITHMETIC)
    assert levels == [
        Decimal("1.000"),
        Decimal("1.050"),
        Decimal("1.100"),
        Decimal("1.150"),
        Decimal("1.200"),
    ]


def test_geometric_levels_monotonic_and_endpoints() -> None:
    levels = build_levels(Decimal("1.00"), Decimal("2.00"), 4, SpacingMode.GEOMETRIC)
    assert levels[0] == Decimal("1.000")
    assert levels[-1] == Decimal("2.000")
    # 等比：相邻比值恒定，间距越往上越大
    assert all(levels[i] < levels[i + 1] for i in range(len(levels) - 1))
    assert (levels[1] - levels[0]) < (levels[-1] - levels[-2])


def test_too_dense_raises() -> None:
    # 区间 0.002、格数 10 → 相邻线在 0.001 tick 下必然重合
    with pytest.raises(ValueError, match="网格太密"):
        build_levels(Decimal("1.000"), Decimal("1.002"), 10, SpacingMode.ARITHMETIC)


def test_bottom_gap() -> None:
    levels = build_levels(Decimal("1.00"), Decimal("1.20"), 4, SpacingMode.ARITHMETIC)
    assert bottom_gap(levels) == Decimal("0.050")


def test_extend_down_uniform_when_factor_one() -> None:
    lines = extend_levels_down(Decimal("1.00"), Decimal("0.05"), Decimal("1"), depth=3)
    assert lines == [Decimal("0.950"), Decimal("0.900"), Decimal("0.850")]


def test_extend_down_widens_with_factor() -> None:
    lines = extend_levels_down(Decimal("1.00"), Decimal("0.05"), Decimal("2"), depth=3)
    # 间距 0.05 → 0.10 → 0.20，越跌格子越宽
    assert lines == [Decimal("0.950"), Decimal("0.850"), Decimal("0.650")]


def test_extend_down_respects_floor() -> None:
    lines = extend_levels_down(
        Decimal("1.00"), Decimal("0.10"), Decimal("1"), depth=5, floor=Decimal("0.80")
    )
    assert lines == [Decimal("0.900"), Decimal("0.800")]


def test_shift_up_arithmetic() -> None:
    new = shift_window_up(
        Decimal("1.00"), Decimal("1.20"), 4, SpacingMode.ARITHMETIC, Decimal("1.35")
    )
    assert new == (Decimal("1.150"), Decimal("1.350"))


def test_shift_up_noop_when_inside() -> None:
    new = shift_window_up(
        Decimal("1.00"), Decimal("1.20"), 4, SpacingMode.ARITHMETIC, Decimal("1.20")
    )
    assert new == (Decimal("1.00"), Decimal("1.20"))


def test_shift_up_geometric_covers_price() -> None:
    lower, upper = shift_window_up(
        Decimal("1.00"), Decimal("2.00"), 4, SpacingMode.GEOMETRIC, Decimal("2.50")
    )
    assert upper >= Decimal("2.50")
    assert lower > Decimal("1.00")
