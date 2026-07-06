"""阶梯状态测试。"""

from collections.abc import Callable
from decimal import Decimal

from vgrid.core import GridConfig
from vgrid.strategy.ladder import Ladder

MakeConfig = Callable[..., GridConfig]


def _amount_at(ladder: Ladder, price: Decimal) -> Decimal:
    for line in ladder.lines:
        if line.price == price:
            return line.buy_amount
    raise AssertionError(f"没有价格为 {price} 的网格线")


def test_base_lines(make_config: MakeConfig) -> None:
    ladder = Ladder(make_config())
    assert ladder.prices == [
        Decimal("1.000"),
        Decimal("1.050"),
        Decimal("1.100"),
        Decimal("1.150"),
        Decimal("1.200"),
    ]
    assert ladder.bottom == Decimal("1.000")
    assert ladder.top == Decimal("1.200")


def test_line_above_below(make_config: MakeConfig) -> None:
    ladder = Ladder(make_config())
    above = ladder.line_above(Decimal("1.10"))
    below = ladder.line_below(Decimal("1.10"))
    assert above is not None and above.price == Decimal("1.150")
    assert below is not None and below.price == Decimal("1.050")


def test_extend_down_widens_gap_and_scales_amount(make_config: MakeConfig) -> None:
    ladder = Ladder(
        make_config(down_spacing_factor=Decimal("2"), down_amount_factor=Decimal("1.5"))
    )
    ladder.ensure_covers_down_to(Decimal("0.80"))

    # 间距 0.05 → 0.10 → 0.20，逐级放大
    assert Decimal("0.950") in ladder.prices
    assert Decimal("0.850") in ladder.prices
    assert Decimal("0.650") in ladder.prices
    assert ladder.bottom == Decimal("0.650")

    # 每格金额按 down_amount_factor 逐级放大：3000 → 4500
    assert _amount_at(ladder, Decimal("0.950")) == Decimal("3000")
    assert _amount_at(ladder, Decimal("0.850")) == Decimal("4500")
    # 基准区间内的线金额不变
    assert _amount_at(ladder, Decimal("1.100")) == Decimal("2000")


def test_shift_up_rebuilds_and_resets_extension(make_config: MakeConfig) -> None:
    ladder = Ladder(make_config())
    ladder.ensure_covers_down_to(Decimal("0.80"))  # 先制造一些延伸
    ladder.shift_up_to(Decimal("1.35"))
    assert ladder.bottom == Decimal("1.150")
    assert ladder.top == Decimal("1.350")
    assert len(ladder.lines) == 5  # 延伸清零，只剩重建的基准阶梯
