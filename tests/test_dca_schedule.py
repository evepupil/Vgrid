"""定投日程测试：频率排期 + K 线映射（顺延 / 去重）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.dca.config import Frequency
from vgrid.dca.schedule import map_to_bars, scheduled_dates


def _bar(d: date) -> Bar:
    one = Decimal("1")
    ts = datetime(d.year, d.month, d.day)
    return Bar(ts=ts, open=one, high=one, low=one, close=one, volume=one)


def test_daily_lists_every_day() -> None:
    days = scheduled_dates(Frequency.DAILY, date(2024, 1, 1), date(2024, 1, 5))
    assert days == [date(2024, 1, d) for d in range(1, 6)]


def test_weekly_picks_weekday() -> None:
    # 2024-01-01 是周一；取周一（ISO weekday=1）
    days = scheduled_dates(Frequency.WEEKLY, date(2024, 1, 1), date(2024, 1, 31), weekday=1)
    assert days == [date(2024, 1, d) for d in (1, 8, 15, 22, 29)]


def test_monthly_picks_day_of_month() -> None:
    days = scheduled_dates(
        Frequency.MONTHLY, date(2024, 1, 1), date(2024, 3, 31), day_of_month=15
    )
    assert days == [date(2024, 1, 15), date(2024, 2, 15), date(2024, 3, 15)]


def test_monthly_clamps_to_month_end() -> None:
    # 2 月没有 31 号 → 钳到 29（2024 闰年）
    days = scheduled_dates(
        Frequency.MONTHLY, date(2024, 2, 1), date(2024, 2, 29), day_of_month=31
    )
    assert days == [date(2024, 2, 29)]


def test_map_holiday_rolls_to_next_bar() -> None:
    # bars 在 Tue/Wed/Thu；周一（假日）的投入日顺延到 Tue（bar0）
    bars = tuple(_bar(d) for d in (date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)))
    idx = map_to_bars([date(2024, 1, 1), date(2024, 1, 3)], bars)
    assert idx == [0, 1]  # Jan1→Tue(bar0)，Jan3→Wed(bar1)


def test_map_dedups_same_bar() -> None:
    # 三个日历日都指向 bar0（重开首日），去重成一次；Jan3 才推进到 bar1
    bars = tuple(_bar(d) for d in (date(2024, 1, 2), date(2024, 1, 3)))
    idx = map_to_bars(
        [date(2023, 12, 30), date(2023, 12, 31), date(2024, 1, 2), date(2024, 1, 3)], bars
    )
    assert idx == [0, 1]  # 前三个落 bar0（去重成一次），Jan3 → bar1


def test_map_stops_past_last_bar() -> None:
    bars = (_bar(date(2024, 1, 2)),)
    idx = map_to_bars([date(2024, 1, 2), date(2024, 6, 1)], bars)
    assert idx == [0]  # 6 月的投入日超出行情，丢弃
