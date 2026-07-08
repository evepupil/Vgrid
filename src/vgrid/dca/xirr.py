"""XIRR：分批投入的真实年化收益。

大白话：每笔钱进场时间不同，把「什么时候投了多少、最后拿回多少」按时间贴现，解出一个
年化收益率 r，让所有现金流的现值加起来正好为 0。定投买入是流出（负），期末清仓价值是
流入（正）。

用二分法解（稳，不挑初值）。现金流方向必须一正一负才有解；否则返回 None（报告显示「—」）。
内部用 float 迭代（利率精度足够），结果转 Decimal。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

_DAYS_PER_YEAR = 365.0
_MAX_ITER = 200
_TOL = 1e-9
_R_LOW = -0.999999  # 下界：(1+r) 不能 ≤ 0
_R_HIGH = 100.0  # 上界：年化 10000%，够覆盖任何正常回测
_MIN_FLOWS = 2  # 至少一笔投入 + 一笔清仓才谈得上年化


def xirr(cash_flows: list[tuple[date, Decimal]]) -> Decimal | None:
    """解不规则现金流的年化收益率；无解返回 None。

    Args:
        cash_flows: ``(日期, 金额)`` 列表，流出为负、流入为正。至少 2 笔且一正一负。
    """
    if len(cash_flows) < _MIN_FLOWS:
        return None
    flows = [(d, float(a)) for d, a in cash_flows]
    if not (any(a > 0 for _, a in flows) and any(a < 0 for _, a in flows)):
        return None  # 全同号，无解

    t0 = min(d for d, _ in flows)
    years = [(d - t0).days / _DAYS_PER_YEAR for d, _ in flows]
    amounts = [a for _, a in flows]

    def npv(rate: float) -> float:
        total = 0.0
        for a, t in zip(amounts, years, strict=True):
            total += a / (1.0 + rate) ** t
        return total

    lo, hi = _R_LOW, _R_HIGH
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None  # 区间内没变号，二分兜不住

    for _ in range(_MAX_ITER):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < _TOL:
            return _to_decimal(mid)
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return _to_decimal((lo + hi) / 2.0)


def _to_decimal(rate: float) -> Decimal:
    """年化收益率转 Decimal（保 6 位小数，够展示）。"""
    return Decimal(str(rate)).quantize(Decimal("0.000001"))
