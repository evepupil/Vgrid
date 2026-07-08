"""XIRR 求解测试。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from vgrid.dca.xirr import xirr


def test_single_year_10pct() -> None:
    # 投 1000，一年后拿回 1100 → 年化 10%
    r = xirr([(date(2024, 1, 1), Decimal("-1000")), (date(2025, 1, 1), Decimal("1100"))])
    assert r is not None
    assert abs(r - Decimal("0.1")) < Decimal("0.001")


def test_loss_gives_negative() -> None:
    r = xirr([(date(2024, 1, 1), Decimal("-1000")), (date(2025, 1, 1), Decimal("900"))])
    assert r is not None
    assert r < 0


def test_multiple_investments_positive() -> None:
    # 两笔投入、期末总回收 > 投入 → 年化为正
    flows = [
        (date(2024, 1, 1), Decimal("-1000")),
        (date(2024, 7, 1), Decimal("-1000")),
        (date(2025, 1, 1), Decimal("2200")),
    ]
    r = xirr(flows)
    assert r is not None
    assert r > 0


def test_all_same_sign_no_solution() -> None:
    assert xirr([(date(2024, 1, 1), Decimal("-1000")), (date(2025, 1, 1), Decimal("-500"))]) is None


def test_single_flow_none() -> None:
    assert xirr([(date(2024, 1, 1), Decimal("-1000"))]) is None
