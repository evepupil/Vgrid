"""金额 / 价格 / 份额的量化工具。

全系统金额与价格一律用 ``Decimal``，杜绝浮点误差。份额是 ``int``，且必须是
一手（100 份）的整数倍。
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

#: ETF 一手 = 100 份，最小交易单位。
LOT_SIZE = 100

#: ETF 价格最小变动单位 0.001 元。
PRICE_TICK = Decimal("0.001")

#: 金额最小单位 1 分。
CENT = Decimal("0.01")


def quantize_price(price: Decimal, tick: Decimal = PRICE_TICK) -> Decimal:
    """把价格对齐到最小变动单位（四舍五入）。"""
    return price.quantize(tick, rounding=ROUND_HALF_UP)


def quantize_cash(amount: Decimal) -> Decimal:
    """把金额对齐到分（四舍五入）。"""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def shares_for_amount(amount: Decimal, price: Decimal, lot_size: int = LOT_SIZE) -> int:
    """给定预算和价格，算出向下取整到整手的可买份额。

    例：预算 2100 元、价格 1.05 元、一手 100 份 → 2000 份（20 手），
    因为 2100/1.05 = 2000 刚好整手；若买不满一手则返回 0。
    """
    if price <= 0:
        raise ValueError(f"价格必须为正：{price}")
    raw_shares = (amount / price).to_integral_value(rounding=ROUND_DOWN)
    lots = (raw_shares / lot_size).to_integral_value(rounding=ROUND_DOWN)
    return int(lots) * lot_size
