"""notify 推送测试（mock HTTP，不真发）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.core.enums import Side
from vgrid.core.models import Fill
from vgrid.notify import PushPlusNotifier, ServerChanNotifier, make_notifier
from vgrid.notify.base import Notifier, format_fills


def _fill(
    *,
    side: Side = Side.BUY,
    price: str = "1.10",
    shares: int = 1000,
    realized_pnl: Decimal | None = None,
    ts: datetime | None = datetime(2026, 7, 7, 10, 30, 0),
) -> Fill:
    return Fill(
        side=side,
        price=Decimal(price),
        shares=shares,
        fee=Decimal("0.10"),
        level_index=0,
        ts=ts,
        realized_pnl=realized_pnl,
    )


def test_format_fills_buy() -> None:
    text = format_fills([_fill()], symbol="159920")
    assert "159920" in text
    assert "买入" in text
    assert "1.10" in text
    assert "10:30:00" in text


def test_format_fills_sell_with_pnl() -> None:
    text = format_fills(
        [_fill(side=Side.SELL, price="1.20", realized_pnl=Decimal("12.34"))], symbol="510300"
    )
    assert "卖出" in text
    assert "已实现 12.34" in text


def test_serverchan_calls_post_form(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_post_form(url: str, fields: dict[str, str]) -> None:
        calls.append((url, fields))

    monkeypatch.setattr("vgrid.notify.serverchan.post_form", fake_post_form)
    ServerChanNotifier("KEY123").send([_fill()], symbol="159920")
    assert len(calls) == 1
    url, fields = calls[0]
    assert "KEY123" in url
    assert fields["title"] == "网格 159920 1 笔"
    assert "买入" in fields["desp"]


def test_pushplus_calls_post_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> None:
        calls.append((url, payload))

    monkeypatch.setattr("vgrid.notify.pushplus.post_json", fake_post_json)
    PushPlusNotifier("TOKEN").send([_fill(), _fill(side=Side.SELL)], symbol="159920")
    assert len(calls) == 1
    url, payload = calls[0]
    assert url == "https://www.pushplus.plus/send"
    assert payload["token"] == "TOKEN"
    assert payload["title"] == "网格 159920 2 笔"
    assert isinstance(payload["content"], str)


def test_send_empty_fills_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_post_form(url: str, fields: dict[str, str]) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("vgrid.notify.serverchan.post_form", fake_post_form)
    ServerChanNotifier("KEY").send([], symbol="159920")
    assert not called


def test_make_notifier_missing_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVERCHAN_SENDKEY", raising=False)
    monkeypatch.delenv("PUSHPLUS_TOKEN", raising=False)
    with pytest.raises(ValueError):
        make_notifier("serverchan")
    with pytest.raises(ValueError):
        make_notifier("pushplus")


def test_make_notifier_unknown_channel() -> None:
    with pytest.raises(ValueError):
        make_notifier("email")


def test_make_notifier_builds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVERCHAN_SENDKEY", "KEY")
    n = make_notifier("serverchan")
    assert isinstance(n, ServerChanNotifier)
    assert isinstance(n, Notifier)  # runtime_checkable 协议


def test_notifier_protocol_structural() -> None:
    """ServerChan / PushPlus 结构满足 Notifier 协议（runtime_checkable）。"""
    assert isinstance(ServerChanNotifier("k"), Notifier)
    assert isinstance(PushPlusNotifier("t"), Notifier)
