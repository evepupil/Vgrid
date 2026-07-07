"""网格阶梯生成：纯函数，只算价格，不涉及订单和状态。

概念：
- 一条「阶梯」是从低到高排好的一串网格线价格 ``levels``，``levels[0]`` 最低。
- 相邻两条线之间是一个「格子」，第 i 个格子在 ``levels[i]`` 和 ``levels[i+1]`` 之间。

本模块提供三块能力：
1. ``build_levels``    —— 按等差 / 等比生成基准阶梯。
2. ``bottom_gap``      —— 取基准阶梯最底部那格的间距，作为向下延伸的起始步长。
3. ``shift_window_up`` —— 冲破上沿后整窗上移，保持几何形状不变（追踪）。

向下延伸（跌破下沿后逐级放大格距）的实现在 ``ladder.Ladder._extend_one``——它要按
深度放大每格金额，是有状态的增量操作，放在 ``Ladder`` 里更合适，不在这里再放一份
纯函数，免得两处实现分叉。
"""

from decimal import ROUND_CEILING, Decimal

from vgrid.core.enums import SpacingMode
from vgrid.core.money import PRICE_TICK, quantize_price


def build_levels(
    lower: Decimal,
    upper: Decimal,
    count: int,
    mode: SpacingMode,
    price_tick: Decimal = PRICE_TICK,
) -> list[Decimal]:
    """生成基准阶梯的 ``count + 1`` 条网格线（含端点），从低到高。

    - 等差：每格固定「元数」，``step = (upper - lower) / count``。
    - 等比：每格固定「百分比」，``ratio = (upper / lower) ** (1/count)``。

    端点 ``lower`` / ``upper`` 精确对齐到最小变动单位；等比的中间线也对齐。
    若因格数过密导致相邻网格线在最小变动单位下重合，抛 ``ValueError``。
    """
    if count < 1:
        raise ValueError(f"格数至少为 1：{count}")
    if lower <= 0 or upper <= lower:
        raise ValueError(f"区间非法：lower={lower}, upper={upper}")

    levels: list[Decimal] = [quantize_price(lower, price_tick)]
    if mode is SpacingMode.ARITHMETIC:
        step = (upper - lower) / count
        for i in range(1, count):
            levels.append(quantize_price(lower + step * i, price_tick))
    else:  # GEOMETRIC
        ratio = (upper / lower) ** (Decimal(1) / Decimal(count))
        price = lower
        for _ in range(1, count):
            price = price * ratio
            levels.append(quantize_price(price, price_tick))
    levels.append(quantize_price(upper, price_tick))

    _assert_strictly_increasing(levels)
    return levels


def bottom_gap(levels: list[Decimal]) -> Decimal:
    """基准阶梯最底部那格的间距（``levels[1] - levels[0]``）。

    作为向下延伸的起始步长——延伸的第一格与它一样宽，之后逐级放大，
    这样从基准区间过渡到延伸区间是平滑的。
    """
    if len(levels) < 2:  # noqa: PLR2004 —— 至少两条线才谈得上间距
        raise ValueError("阶梯至少要有两条网格线")
    return levels[1] - levels[0]


def shift_window_up(
    lower: Decimal,
    upper: Decimal,
    count: int,
    mode: SpacingMode,
    price: Decimal,
    price_tick: Decimal = PRICE_TICK,
) -> tuple[Decimal, Decimal]:
    """价格冲破上沿后，把整个网格窗口上移，直到 ``price`` 落回窗口内。

    保持网格几何不变：等差按整数格步长上移，等比按 ``ratio`` 整数次幂放大。
    返回新的 ``(lower, upper)``。若 ``price`` 未超过 ``upper``，原样返回。
    """
    if price <= upper:
        return (lower, upper)

    if mode is SpacingMode.ARITHMETIC:
        step = (upper - lower) / count
        steps = ((price - upper) / step).to_integral_value(rounding=ROUND_CEILING)
        shift = step * steps
        new_lower = lower + shift
        new_upper = upper + shift
    else:  # GEOMETRIC
        ratio = (upper / lower) ** (Decimal(1) / Decimal(count))
        new_lower, new_upper = lower, upper
        # 逐次放大直到覆盖 price，ratio > 1 保证收敛。
        while new_upper < price:
            new_lower = new_lower * ratio
            new_upper = new_upper * ratio

    return (quantize_price(new_lower, price_tick), quantize_price(new_upper, price_tick))


def _assert_strictly_increasing(levels: list[Decimal]) -> None:
    for i in range(len(levels) - 1):
        if levels[i] >= levels[i + 1]:
            raise ValueError("网格太密：相邻网格线在最小变动单位下重合，请减少格数或放宽区间")
