"""市场时段状态（FR-11.2）：交易中 / 午休 / 已收盘 / 未开盘。纯函数，单测重点。

按市场的交易时段窗口判断——沪深 A 股 09:30–11:30 / 13:00–15:00，港股 09:30–12:00 /
13:00–16:00。周末休市。**已知限制**：只按星期几判休市，不含法定节假日日历（需外部日历
数据，暂缺）；节假日会被误判为交易日，接入 akshare 交易日历后可补。传入的 ``now`` 视作
市场所在时区（东八区）的本地时间。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

_SATURDAY = 5  # weekday() ≥ 此值即周末

# 每个市场的交易时段（上午 / 下午），(开, 收)
_SESSIONS: dict[str, tuple[tuple[time, time], ...]] = {
    "沪深": ((time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))),
    "港股": ((time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))),
}

# status → 中文标签
_LABELS = {
    "trading": "交易中",
    "lunch": "午休",
    "pre_open": "未开盘",
    "closed": "已收盘",
    "weekend": "休市",
}


@dataclass(frozen=True, slots=True)
class MarketStatus:
    """市场时段状态。"""

    market: str
    status: str  # trading / lunch / pre_open / closed / weekend
    label: str  # 中文
    now: datetime
    note: str


def market_status(now: datetime, market: str = "沪深") -> MarketStatus:
    """按 ``now`` 判断 ``market`` 的时段状态。未知 market 回落到沪深窗口。"""
    sessions = _SESSIONS.get(market, _SESSIONS["沪深"])
    if now.weekday() >= _SATURDAY:
        return _mk(market, "weekend", now, "周末休市")

    t = now.time()
    first_open = sessions[0][0]
    last_close = sessions[-1][1]

    if t < first_open:
        return _mk(market, "pre_open", now, f"{_hm(first_open)} 开盘")
    if t >= last_close:
        return _mk(market, "closed", now, "今日已收盘")
    for open_t, close_t in sessions:
        if open_t <= t < close_t:
            return _mk(market, "trading", now, f"{_hm(close_t)} 休/收")
    # 落在两段之间 = 午休
    return _mk(market, "lunch", now, "午间休市")


def _mk(market: str, status: str, now: datetime, note: str) -> MarketStatus:
    return MarketStatus(market=market, status=status, label=_LABELS[status], now=now, note=note)


def _hm(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"
