"""报告数值格式化工具：百分比 / 小数 / 金额统一格式。"""

from __future__ import annotations

from decimal import Decimal

from vgrid.core.money import quantize_cash


def pct(ratio: Decimal, digits: int = 2) -> str:
    """比例 → 百分比字符串：``0.1234`` → ``'12.34%'``。"""
    q = Decimal(1).scaleb(-digits)  # 10^-digits
    return f"{(ratio * 100).quantize(q)}%"


def dec(value: Decimal, digits: int = 2) -> str:
    """Decimal 固定小数位字符串。"""
    q = Decimal(1).scaleb(-digits)
    return str(value.quantize(q))


def cash(value: Decimal) -> str:
    """金额对齐到分。"""
    return str(quantize_cash(value))
