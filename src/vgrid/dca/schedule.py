"""定投日程：按频率算出日历投入日，再映射到实际 K 线。

两步走，纯函数：
1. ``scheduled_dates``：按频率（日 / 周 / 月）在 [start, end] 里排出**日历投入日**，
   不管是不是交易日。
2. ``map_to_bars``：把每个日历日映射到「日期 ≥ 它的第一根 K 线」——用 K 线本身当交易日历，
   撞上周末 / 节假日就顺延到下一个有行情的交易日，**不需要单独的节假日表**。同一根 K 线
   最多买一次（去重），避免连续假期把多期堆到重开首日。
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from vgrid.core.bar import Bar
from vgrid.dca.config import Frequency


def scheduled_dates(
    frequency: Frequency,
    start: date,
    end: date,
    *,
    weekday: int = 1,
    day_of_month: int = 1,
) -> list[date]:
    """按频率排出 [start, end] 内的日历投入日（升序）。"""
    if start > end:
        return []
    if frequency is Frequency.DAILY:
        return _daily(start, end)
    if frequency is Frequency.WEEKLY:
        return [d for d in _daily(start, end) if d.isoweekday() == weekday]
    return _monthly(start, end, day_of_month)


def map_to_bars(scheduled: list[date], bars: tuple[Bar, ...]) -> list[int]:
    """把日历投入日映射到 K 线下标（升序、去重）。

    每个日历日 → 日期 ≥ 它的第一根 K 线。指针 ``j`` 单调前移，一根 K 线只买一次
    （连续假期后多期日历日会指向同一根重开 K 线，只保留一次）。
    """
    indices: list[int] = []
    seen: set[int] = set()
    j = 0
    n = len(bars)
    for d in scheduled:
        while j < n and bars[j].ts.date() < d:
            j += 1
        if j >= n:
            break  # 后面的日历日都超出行情了
        if j not in seen:
            seen.add(j)
            indices.append(j)
    return indices


def _daily(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def _monthly(start: date, end: date, day_of_month: int) -> list[date]:
    """每月 ``day_of_month`` 号（超当月天数钳到月末）落在 [start, end] 的日子。"""
    out: list[date] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        last_day = calendar.monthrange(year, month)[1]
        target = date(year, month, min(day_of_month, last_day))
        if start <= target <= end:
            out.append(target)
        month += 1
        if month > 12:  # noqa: PLR2004  12 月是年界，含义明确
            year, month = year + 1, 1
    return out
