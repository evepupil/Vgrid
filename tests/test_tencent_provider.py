"""腾讯 provider：字段映射 + 前缀 + 分段 + adjust（mock requests，不打网）。

重点验证腾讯字段顺序 ``date, open, close, high, low, volume``（close 在第 3 位）
正确映射到标准 Bar——这是最容易翻车的点。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from vgrid.core.enums import Frame
from vgrid.data.tencent_provider import (
    TencentProvider,
    _split_by_year,
    _tencent_symbol,
)


class _FakeResp:
    """模拟 requests.Response：只暴露 raise_for_status / json。"""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._payload


def _ok(rows: list[list[str]], code: str = "sz159920") -> dict[str, Any]:
    """构造腾讯成功返回的 payload，qfqday 放指定行。"""
    return {"code": 0, "data": {code: {"qfqday": rows}}}


def test_invalid_adjust_rejected() -> None:
    with pytest.raises(ValueError, match="不支持的 adjust"):
        TencentProvider(adjust="xxx")


def test_tencent_symbol_prefix() -> None:
    assert _tencent_symbol("159920") == "sz159920"  # 深市
    assert _tencent_symbol("510300") == "sh510300"  # 沪市 5 开头


def test_split_by_year_full_years() -> None:
    segs = _split_by_year(date(2022, 1, 1), date(2024, 12, 31))
    assert segs == [
        (date(2022, 1, 1), date(2022, 12, 31)),
        (date(2023, 1, 1), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 12, 31)),
    ]


def test_split_by_year_partial() -> None:
    """跨年但起止落在年中：两端截到各自的年内边界。"""
    segs = _split_by_year(date(2023, 6, 1), date(2024, 3, 15))
    assert segs == [
        (date(2023, 6, 1), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 3, 15)),
    ]


def test_fetch_maps_tencent_field_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """腾讯 close 在第 3 位、high 在第 4 位、low 在第 5 位，验证正确落到 Bar。"""
    rows = [
        # [date, open, close, high, low, volume]
        ["2024-01-02", "1.00", "1.03", "1.05", "0.99", "100"],
        ["2024-01-03", "1.01", "1.04", "1.06", "1.00", "200"],
    ]
    captured: dict[str, Any] = {}

    def _fake(url: str, params: dict[str, str] | None = None, timeout: int = 0) -> _FakeResp:
        captured["url"] = url
        captured["params"] = params
        return _FakeResp(_ok(rows))

    monkeypatch.setattr("vgrid.data.tencent_provider.requests.get", _fake)
    series = TencentProvider().fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)

    # param 含 sz 前缀、640 count、qfq
    assert captured["params"]["param"] == "sz159920,day,2024-01-02,2024-01-03,640,qfq"
    assert len(series) == 2
    b = series[0]
    assert b.ts.date() == date(2024, 1, 2)
    assert b.open == Decimal("1.00")
    assert b.close == Decimal("1.03")  # 腾讯第 3 位，不是第 5 位
    assert b.high == Decimal("1.05")  # 腾讯第 4 位
    assert b.low == Decimal("0.99")  # 腾讯第 5 位
    assert b.volume == Decimal("100")


def test_fetch_sh_prefix_for_sh_etf(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _fake(url: str, params: dict[str, str] | None = None, timeout: int = 0) -> _FakeResp:
        captured["params"] = params
        return _FakeResp(_ok([["2024-01-02", "1", "1", "1", "1", "1"]], code="sh510300"))

    monkeypatch.setattr("vgrid.data.tencent_provider.requests.get", _fake)
    TencentProvider().fetch("510300", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)
    assert captured["params"]["param"].startswith("sh510300,day")


def test_fetch_rejects_minute_frame() -> None:
    prov = TencentProvider()
    with pytest.raises(ValueError, match="只支持日线"):
        prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.MINUTE)


def test_fetch_segments_multi_year_and_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    """跨年区间分段请求 + 合并；跨段同一天去重。"""
    by_year: dict[int, dict[str, Any]] = {
        2022: _ok(
            [
                ["2022-12-30", "1", "1", "1", "1", "1"],
                ["2022-12-31", "1", "1", "1", "1", "1"],
            ]
        ),
        2023: _ok(
            [
                ["2022-12-31", "1", "1", "1", "1", "1"],  # 和上段重叠，去重
                ["2023-01-03", "1", "1", "1", "1", "1"],
            ]
        ),
    }
    calls: list[int] = []

    def _fake(url: str, params: dict[str, str] | None = None, timeout: int = 0) -> _FakeResp:
        assert params is not None
        start_str = params["param"].split(",")[2]  # "YYYY-MM-DD"
        year = int(start_str[:4])
        calls.append(year)
        return _FakeResp(by_year[year])

    monkeypatch.setattr("vgrid.data.tencent_provider.requests.get", _fake)
    series = TencentProvider().fetch("159920", date(2022, 12, 30), date(2023, 12, 31), Frame.DAILY)

    assert sorted(calls) == [2022, 2023]  # 分两段请求
    # 2022-12-31 重叠去重，剩 3 个交易日
    assert [b.ts.date() for b in series] == [
        date(2022, 12, 30),
        date(2022, 12, 31),
        date(2023, 1, 3),
    ]


def test_fetch_adjust_hfq_uses_hfqday(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    payload = {"data": {"sz159920": {"hfqday": [["2024-01-02", "1", "1", "1", "1", "1"]]}}}

    def _fake(url: str, params: dict[str, str] | None = None, timeout: int = 0) -> _FakeResp:
        captured["params"] = params
        return _FakeResp(payload)

    monkeypatch.setattr("vgrid.data.tencent_provider.requests.get", _fake)
    TencentProvider(adjust="hfq").fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)
    assert ",hfq" in captured["params"]["param"]


def test_fetch_empty_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """data 为空时返回空序列，不抛异常。"""

    def _fake(url: str, params: dict[str, str] | None = None, timeout: int = 0) -> _FakeResp:
        return _FakeResp({"data": {}})

    monkeypatch.setattr("vgrid.data.tencent_provider.requests.get", _fake)
    series = TencentProvider().fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)
    assert len(series) == 0
