"""mootdx provider：字段映射 + 翻页 + 区间过滤 + 去重（mock Quotes，不打网）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from vgrid.core.enums import Frame
from vgrid.data.mootdx_provider import MootdxProvider, symbol_exists


def _df(rows: list[tuple[str, float, float, float, float, int]]) -> pd.DataFrame:
    """构造 mootdx 风格 DataFrame：DatetimeIndex + open/high/low/close/volume。"""
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
            "volume": [r[5] for r in rows],
        },
        index=idx,
    )


class _FakeClient:
    """模拟 mootdx client：按页（start//offset）返回预设 DataFrame，记录调用。"""

    def __init__(self, pages: list[pd.DataFrame]) -> None:
        self._pages = pages
        self.calls: list[tuple[int, int]] = []  # (frequency, start)

    def bars(self, symbol: str, frequency: int, offset: int, start: int) -> pd.DataFrame | None:
        self.calls.append((frequency, start))
        idx = start // offset
        if idx >= len(self._pages):
            return None
        return self._pages[idx]


def _patch(monkeypatch: pytest.MonkeyPatch, pages: list[pd.DataFrame]) -> _FakeClient:
    """monkeypatch Quotes.factory 返回 fake client。"""
    client = _FakeClient(pages)
    monkeypatch.setattr(
        "vgrid.data.mootdx_provider.Quotes",
        SimpleNamespace(factory=lambda **kw: client),
    )
    return client


def test_invalid_frame_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, [])
    prov = MootdxProvider()
    with pytest.raises(ValueError, match="只支持分钟线"):
        prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)


def test_fetch_minute_maps_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _df(
        [
            ("2024-01-02 09:31:00", 1.00, 1.05, 0.99, 1.03, 100),
            ("2024-01-02 09:32:00", 1.01, 1.06, 1.00, 1.04, 200),
        ]
    )
    _patch(monkeypatch, [df])
    series = MootdxProvider().fetch("159920", date(2024, 1, 2), date(2024, 1, 2), Frame.MINUTE)
    assert len(series) == 2
    b = series[0]
    assert b.ts == datetime(2024, 1, 2, 9, 31)
    assert b.open == Decimal("1.00")
    assert b.high == Decimal("1.05")
    assert b.low == Decimal("0.99")
    assert b.close == Decimal("1.03")
    assert b.volume == Decimal("100")


def test_fetch_pagination_until_covers_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """翻页拉到覆盖 start 日期即停；start 之前的过滤掉。"""
    pages = [
        _df([("2024-06-01 09:31:00", 1, 1, 1, 1, 1), ("2024-06-01 09:32:00", 1, 1, 1, 1, 1)]),
        _df([("2024-05-15 09:31:00", 2, 2, 2, 2, 2), ("2024-05-15 09:32:00", 2, 2, 2, 2, 2)]),
        _df([("2024-05-01 09:31:00", 3, 3, 3, 3, 3), ("2024-05-01 09:32:00", 3, 3, 3, 3, 3)]),
    ]
    client = _patch(monkeypatch, pages)
    series = MootdxProvider().fetch("159920", date(2024, 5, 10), date(2024, 6, 1), Frame.MINUTE)
    # 第三页最早 05-01 < start 05-10，停；共翻 3 页
    assert len(client.calls) == 3
    # 过滤到 [05-10, 06-01]：05-01 那页被过滤，剩 06-01 + 05-15 共 4 根
    assert len(series) == 4


def test_fetch_filters_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """超出 [start, end] 的被过滤。"""
    df = _df(
        [
            ("2024-01-01 09:31:00", 1, 1, 1, 1, 1),
            ("2024-01-02 09:31:00", 2, 2, 2, 2, 2),
            ("2024-01-03 09:31:00", 3, 3, 3, 3, 3),
        ]
    )
    _patch(monkeypatch, [df])
    series = MootdxProvider().fetch("159920", date(2024, 1, 2), date(2024, 1, 2), Frame.MINUTE)
    assert len(series) == 1
    assert series[0].open == Decimal("2")


def test_fetch_dedup_across_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """跨页重复的同一时间戳去重（keep=last，第二页覆盖第一页）。"""
    pages = [
        _df([("2024-01-02 09:31:00", 1, 1, 1, 1, 1)]),
        _df([("2024-01-02 09:31:00", 9, 9, 9, 9, 9), ("2024-01-01 09:31:00", 1, 1, 1, 1, 1)]),
    ]
    _patch(monkeypatch, pages)
    series = MootdxProvider().fetch("159920", date(2024, 1, 1), date(2024, 1, 2), Frame.MINUTE)
    assert len(series) == 2  # 01-01 + 01-02（去重）
    jan2 = next(b for b in series if b.ts.day == 2)
    assert jan2.open == Decimal("9")  # keep=last 取第二页


def test_fetch_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """无数据返回空序列，不抛异常。"""
    _patch(monkeypatch, [])
    series = MootdxProvider().fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.MINUTE)
    assert len(series) == 0


def test_symbol_exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """拉到 K 线 = 代码有效。"""
    fake = SimpleNamespace(fetch=lambda *a, **kw: SimpleNamespace(bars=[1, 2, 3]))
    monkeypatch.setattr("vgrid.data.mootdx_provider._validator", fake)
    assert symbol_exists("159920") is True


def test_symbol_exists_false_no_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """无 K 线 = 代码无效。"""
    fake = SimpleNamespace(fetch=lambda *a, **kw: SimpleNamespace(bars=[]))
    monkeypatch.setattr("vgrid.data.mootdx_provider._validator", fake)
    assert symbol_exists("999999") is False


def test_symbol_exists_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """连接异常也判 False（验不住就拦下，让用户核对代码）。"""

    def boom(*a: object, **kw: object) -> object:
        raise OSError("connect failed")

    monkeypatch.setattr("vgrid.data.mootdx_provider._validator", SimpleNamespace(fetch=boom))
    assert symbol_exists("159920") is False
