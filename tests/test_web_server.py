"""FastAPI 路由测试（TestClient）。"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from vgrid.core import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.store import connect, save_config, save_tick
from vgrid.web.server import create_app


def _cfg() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def test_index_returns_html() -> None:
    client = TestClient(create_app(":memory:"))
    r = client.get("/")
    assert r.status_code == 200
    assert "vgrid" in r.text


def test_api_state_404_when_empty(tmp_path: Path) -> None:
    db = tmp_path / "p.sqlite"
    client = TestClient(create_app(str(db)))
    r = client.get("/api/state")
    assert r.status_code == 404


def test_api_state_returns_json(tmp_path: Path) -> None:
    db = tmp_path / "p.sqlite"
    conn = connect(str(db))
    save_config(conn, _cfg())
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.10"))
    save_tick(conn, datetime(2024, 1, 2, 9, 31), Decimal("1.05"))
    conn.close()
    client = TestClient(create_app(str(db)))
    r = client.get("/api/state")
    assert r.status_code == 200
    j = r.json()
    assert j["symbol"] == "159920"
    assert len(j["equity_curve"]) == 2
    assert "fill_marks" in j
