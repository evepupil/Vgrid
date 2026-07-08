"""净值解析测试（东财场内基金净值原始行 → NavPoint）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from vgrid.income.nav import fetch_navs, parse_nav_rows


def _row(day: str, unit: str, acc: str) -> dict[str, str]:
    return {"净值日期": day, "单位净值": unit, "累计净值": acc, "日增长率": "1.0"}


def test_parse_basic() -> None:
    rows = [_row("2024-01-02", "0.9240", "1.8480")]
    pts = parse_nav_rows(rows)
    assert len(pts) == 1
    assert pts[0].day == date(2024, 1, 2)
    assert pts[0].unit_nav == Decimal("0.9240")
    assert pts[0].acc_nav == Decimal("1.8480")


def test_skips_bad_rows() -> None:
    rows = [
        _row("---", "0.9", "1.8"),  # 日期坏
        _row("2024-01-03", "", "1.8"),  # 单位净值缺
        _row("2024-01-04", "0.95", "1.9"),  # 好
    ]
    pts = parse_nav_rows(rows)
    assert len(pts) == 1
    assert pts[0].day == date(2024, 1, 4)


def test_sorted_by_day() -> None:
    rows = [_row("2024-01-04", "0.95", "1.9"), _row("2024-01-02", "0.92", "1.84")]
    pts = parse_nav_rows(rows)
    assert [p.day.day for p in pts] == [2, 4]


def test_fetch_uses_injected_fetch() -> None:
    rows = [_row("2024-01-02", "0.9240", "1.8480")]
    pts = fetch_navs("512890", date(2024, 1, 1), date(2024, 2, 1), fetch=lambda _s, _a, _b: rows)
    assert len(pts) == 1
