"""回测 API 端点测试（mock load_bars 不打网）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.web import create_app


def _bar(offset: int, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(
        ts=datetime(2024, 1, 1) + timedelta(days=offset),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
        volume=Decimal("100"),
    )


def _bars() -> BarSeries:
    return BarSeries(
        symbol="159920",
        frame=Frame.DAILY,
        bars=(
            _bar(1, "1.00", "1.05", "0.99", "1.03"),
            _bar(2, "1.03", "1.06", "1.00", "1.04"),
        ),
    )


def _config() -> dict[str, object]:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.90"),
        upper_price=Decimal("1.20"),
        grid_count=6,
        per_grid_amount=Decimal("3000"),
        capital_cap=Decimal("50000"),
    ).to_dict()


def _body(config: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "start": "2024-01-02",
        "end": "2024-01-03",
        "frame": "1d",
        "config": config if config is not None else _config(),
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    def _fake(*a: object, **kw: object) -> BarSeries:
        return _bars()

    monkeypatch.setattr("vgrid.web.routes.backtest.load_bars", _fake)
    return TestClient(create_app(strategies_dir=tmp_path))


def test_backtest_ok(client: TestClient) -> None:
    r = client.post("/api/backtest", json=_body())
    assert r.status_code == 200
    j = r.json()
    assert "metrics" in j
    assert j["n_bars"] == 2
    assert len(j["equity_curve"]) == 2


def test_backtest_invalid_config_400(client: TestClient) -> None:
    bad = _config()
    bad["grid_count"] = 0
    r = client.post("/api/backtest", json=_body(bad))
    assert r.status_code == 400


def test_backtest_invalid_frame_400(client: TestClient) -> None:
    body = _body()
    body["frame"] = "5m"
    r = client.post("/api/backtest", json=body)
    assert r.status_code == 400


def test_backtest_no_data_404(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _empty(*a: object, **kw: object) -> BarSeries:
        return BarSeries(symbol="159920", frame=Frame.DAILY, bars=())

    monkeypatch.setattr("vgrid.web.routes.backtest.load_bars", _empty)
    client = TestClient(create_app(strategies_dir=tmp_path))
    r = client.post("/api/backtest", json=_body())
    assert r.status_code == 404
