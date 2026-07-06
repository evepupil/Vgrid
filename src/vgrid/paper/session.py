"""A 股交易时段判断。

A 股工作日：上午 09:30–11:30、下午 13:00–15:00。周末非盘中。法定节假日按非盘中处理
（节假日数据 akshare 会缺，盘中轮询拿到的价为最近收盘价，影响不大；精确判断要交易日历，
留作后续）。
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

_MORNING_START = time(9, 30)
_MORNING_END = time(11, 30)
_AFTERNOON_START = time(13, 0)
_AFTERNOON_END = time(15, 0)
_WEEKDAYS = 5  # 周一..周五；weekday() < 5 为工作日，>= 5 为周末


def in_session(now: datetime) -> bool:
    """是否在 A 股交易时段内。"""
    if now.weekday() >= _WEEKDAYS:
        return False
    t = now.time()
    if _MORNING_START <= t <= _MORNING_END:
        return True
    return _AFTERNOON_START <= t <= _AFTERNOON_END


def next_session_open(now: datetime) -> datetime:
    """下一个开盘点：今天还有开盘段就取今天，否则取下一个工作日 09:30。"""
    t = now.time()
    if now.weekday() < _WEEKDAYS:
        if t < _MORNING_START:
            return datetime.combine(now.date(), _MORNING_START)
        if _MORNING_END < t < _AFTERNOON_START:
            return datetime.combine(now.date(), _AFTERNOON_START)
    d = now.date()
    for _ in range(7):  # 一周内必有工作日
        d = d + timedelta(days=1)
        if d.weekday() < _WEEKDAYS:
            return datetime.combine(d, _MORNING_START)
    raise RuntimeError("7 天内找不到工作日（不可能）")
