"""市场时段纯函数测试：交易/午休/收盘/未开盘/周末，含沪深与港股窗口差异。"""

from __future__ import annotations

from datetime import datetime

from vgrid.web.market import market_status

# 2024-06-03 是周一（工作日），2024-06-08 是周六
_MON = "2024-06-03"
_SAT = "2024-06-08"


def _at(day: str, hh: int, mm: int) -> datetime:
    return datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:00")


def test_trading_midmorning() -> None:
    s = market_status(_at(_MON, 10, 0), "沪深")
    assert s.status == "trading"
    assert s.label == "交易中"


def test_lunch_break() -> None:
    s = market_status(_at(_MON, 12, 0), "沪深")  # 11:30~13:00 午休
    assert s.status == "lunch"
    assert s.label == "午休"


def test_pre_open() -> None:
    s = market_status(_at(_MON, 9, 0), "沪深")
    assert s.status == "pre_open"


def test_after_close() -> None:
    s = market_status(_at(_MON, 15, 30), "沪深")  # 15:00 收盘后
    assert s.status == "closed"
    assert s.label == "已收盘"


def test_weekend_is_closed() -> None:
    s = market_status(_at(_SAT, 10, 0), "沪深")
    assert s.status == "weekend"
    assert "周末" in s.note


def test_hk_vs_ashare_window_differs() -> None:
    # 11:45：沪深午休（11:30 收），港股仍交易（12:00 才收）
    t = _at(_MON, 11, 45)
    assert market_status(t, "沪深").status == "lunch"
    assert market_status(t, "港股").status == "trading"


def test_unknown_market_falls_back_to_ashare() -> None:
    s = market_status(_at(_MON, 10, 0), "火星所")
    assert s.status == "trading"  # 用沪深窗口
