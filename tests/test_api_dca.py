"""定投回测 API 端点测试（mock load_bars 不打网）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.dca.config import DcaConfig, Frequency
from vgrid.web import create_app


def _bar(offset: int, price: str) -> Bar:
    p = Decimal(price)
    return Bar(
        ts=datetime(2024, 1, 2) + timedelta(days=offset),
        open=p,
        high=p,
        low=p,
        close=p,
        volume=Decimal("100"),
    )


def _bars() -> BarSeries:
    return BarSeries(
        symbol="159920",
        frame=Frame.DAILY,
        bars=tuple(_bar(i, f"{1.00 + i * 0.01:.2f}") for i in range(4)),
    )


def _config() -> dict[str, object]:
    return DcaConfig(
        symbol="159920",
        frequency=Frequency.DAILY,
        base_amount=Decimal("2000"),
        cash_cap=Decimal("50000"),
    ).to_dict()


def _body(config: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "start": "2024-01-02",
        "end": "2024-01-05",
        "frame": "1d",
        "config": config if config is not None else _config(),
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    def _fake(*a: object, **kw: object) -> BarSeries:
        return _bars()

    monkeypatch.setattr("vgrid.web.routes.dca.load_bars", _fake)
    return TestClient(create_app(strategies_dir=tmp_path))


def test_dca_backtest_ok(client: TestClient) -> None:
    r = client.post("/api/dca/backtest", json=_body())
    assert r.status_code == 200
    j = r.json()
    assert j["n_bars"] == 4
    assert j["metrics"]["n_buys"] == 4  # 每日投一次，4 根全买
    assert "invested_amount" in j["metrics"]
    assert "xirr" in j["metrics"]  # 可能为 null，但字段在
    assert len(j["equity_curve"]) == 4
    assert len(j["buy_hold_curve"]) == 4
    assert len(j["trades"]) == 4


def test_dca_backtest_invalid_config_400(client: TestClient) -> None:
    bad = _config()
    bad["base_amount"] = "0"  # 非法
    r = client.post("/api/dca/backtest", json=_body(bad))
    assert r.status_code == 400


def test_dca_backtest_invalid_frame_400(client: TestClient) -> None:
    body = _body()
    body["frame"] = "xxx"
    r = client.post("/api/dca/backtest", json=body)
    assert r.status_code == 400


def test_dca_backtest_no_data_404(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _empty(*a: object, **kw: object) -> BarSeries:
        return BarSeries(symbol="159920", frame=Frame.DAILY, bars=())

    monkeypatch.setattr("vgrid.web.routes.dca.load_bars", _empty)
    client = TestClient(create_app(strategies_dir=tmp_path))
    r = client.post("/api/dca/backtest", json=_body())
    assert r.status_code == 404


def test_dca_backtest_symbol_overrides_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def _fake_load(symbol: str, *a: object, **kw: object) -> BarSeries:
        captured["symbol"] = symbol
        return _bars()

    monkeypatch.setattr("vgrid.web.routes.dca.load_bars", _fake_load)
    client = TestClient(create_app(strategies_dir=tmp_path))
    body = _body()
    body["symbol"] = "510300"
    r = client.post("/api/dca/backtest", json=body)
    assert r.status_code == 200
    assert captured["symbol"] == "510300"
