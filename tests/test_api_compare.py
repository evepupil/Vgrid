"""策略对比 API 端点测试（mock load_bars 不打网）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.dca.config import DcaConfig, Frequency
from vgrid.web import create_app


def _bars() -> BarSeries:
    bars = []
    for i in range(30):
        p = Decimal(str(round(1.00 + 0.01 * i, 3)))
        bars.append(
            Bar(
                ts=datetime(2024, 1, 1) + timedelta(days=i),
                open=p,
                high=p,
                low=p,
                close=p,
                volume=Decimal("100"),
            )
        )
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=tuple(bars))


def _grid_config() -> dict[str, object]:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.90"),
        upper_price=Decimal("1.50"),
        grid_count=10,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    ).to_dict()


def _dca_config() -> dict[str, object]:
    return DcaConfig(
        symbol="159920",
        frequency=Frequency.DAILY,
        base_amount=Decimal("2000"),
        cash_cap=Decimal("50000"),
    ).to_dict()


def _body(**over: object) -> dict[str, object]:
    body: dict[str, object] = {
        "symbol": "159920",
        "start": "2024-01-01",
        "end": "2024-01-30",
        "frame": "1d",
        "grid_config": _grid_config(),
        "dca_config": _dca_config(),
    }
    body.update(over)
    return body


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    def _fake(*a: object, **kw: object) -> BarSeries:
        return _bars()

    monkeypatch.setattr("vgrid.web.routes.compare.load_bars", _fake)
    return TestClient(create_app(strategies_dir=tmp_path))


def test_compare_three_rows_with_curves(client: TestClient) -> None:
    r = client.post("/api/compare", json=_body())
    assert r.status_code == 200
    j = r.json()
    names = [row["name"] for row in j["rows"]]
    assert names == ["网格", "定投", "买入持有"]
    assert j["initial_cash"] == "50000"
    for row in j["rows"]:
        assert len(row["curve"]) == 30  # 每策略一条净值曲线
    dca_row = next(row for row in j["rows"] if row["name"] == "定投")
    assert dca_row["invested"] is not None
    bh_row = next(row for row in j["rows"] if row["name"] == "买入持有")
    assert bh_row["invested"] is None  # 买入持有没有投入/XIRR


def test_compare_grid_only(client: TestClient) -> None:
    r = client.post("/api/compare", json=_body(dca_config=None))
    assert r.status_code == 200
    assert [row["name"] for row in r.json()["rows"]] == ["网格", "买入持有"]


def test_compare_needs_a_config(client: TestClient) -> None:
    r = client.post("/api/compare", json=_body(grid_config=None, dca_config=None))
    assert r.status_code == 400


def test_compare_initial_cash_override(client: TestClient) -> None:
    r = client.post("/api/compare", json=_body(initial_cash="80000"))
    assert r.status_code == 200
    assert r.json()["initial_cash"] == "80000"


def test_compare_no_data_404(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _empty(*a: object, **kw: object) -> BarSeries:
        return BarSeries(symbol="159920", frame=Frame.DAILY, bars=())

    monkeypatch.setattr("vgrid.web.routes.compare.load_bars", _empty)
    client = TestClient(create_app(strategies_dir=tmp_path))
    r = client.post("/api/compare", json=_body())
    assert r.status_code == 404
