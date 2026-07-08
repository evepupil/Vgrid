"""分红明细解析测试（东财"分红送配详情"原始行 → DividendEvent）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from vgrid.income.dividends import fetch_dividends, parse_dividend_rows


def _row(reg: str, ex: str, amount: str, pay: str) -> dict[str, str]:
    return {"权益登记日": reg, "除息日": ex, "每份分红": amount, "分红发放日": pay}


def test_parse_per_share_and_dates() -> None:
    rows = [_row("2025-01-20", "2025-01-21", "每份派现金0.1420元", "2025-01-24")]
    evs = parse_dividend_rows(rows)
    assert len(evs) == 1
    e = evs[0]
    assert e.register_date == date(2025, 1, 20)
    assert e.ex_date == date(2025, 1, 21)
    assert e.pay_date == date(2025, 1, 24)
    assert e.per_share == Decimal("0.1420")


def test_per_ten_shares_normalized() -> None:
    rows = [_row("2024-01-01", "2024-01-02", "每10份派现金1.420元", "2024-01-05")]
    assert parse_dividend_rows(rows)[0].per_share == Decimal("0.142")


def test_skips_unparseable_rows() -> None:
    rows = [
        _row("2024-01-01", "2024-01-02", "分红方案尚未公布", "2024-01-05"),  # 无金额
        _row("2024-01-01", "无效日期", "每份派现金0.1元", "2024-01-05"),  # 除息日坏
        _row("2024-01-01", "2024-01-02", "每份派现金0.1元", "2024-01-05"),  # 好
    ]
    evs = parse_dividend_rows(rows)
    assert len(evs) == 1
    assert evs[0].per_share == Decimal("0.1")


def test_missing_dates_fall_back_to_ex() -> None:
    rows = [{"除息日": "2024-01-02", "每份分红": "每份派现金0.1元"}]  # 缺登记日/发放日
    e = parse_dividend_rows(rows)[0]
    assert e.register_date == date(2024, 1, 2)
    assert e.pay_date == date(2024, 1, 2)


def test_sorted_by_ex_date() -> None:
    rows = [
        _row("2025-01-20", "2025-01-21", "每份派现金0.14元", "2025-01-24"),
        _row("2023-01-13", "2023-01-16", "每份派现金0.13元", "2023-01-19"),
        _row("2024-01-22", "2024-01-23", "每份派现金0.13元", "2024-01-26"),
    ]
    evs = parse_dividend_rows(rows)
    assert [e.ex_date.year for e in evs] == [2023, 2024, 2025]


def test_fetch_uses_injected_fetch() -> None:
    rows = [_row("2025-01-20", "2025-01-21", "每份派现金0.14元", "2025-01-24")]
    evs = fetch_dividends("510880", fetch=lambda _s: rows)
    assert len(evs) == 1
