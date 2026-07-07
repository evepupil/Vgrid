"""portfolio API 端点测试。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from vgrid.core.config import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.store import connect, save_config, save_tick
from vgrid.web import create_app


def _cfg(symbol: str = "159920") -> GridConfig:
    return GridConfig(
        symbol=symbol,
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(data_dir=tmp_path))


def _seed(tmp_path: Path, name: str, *, symbol: str = "159920", mode: str = "sim") -> None:
    paper_dir = tmp_path / "paper" / mode
    paper_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(str(paper_dir / f"{name}.sqlite"))
    save_config(conn, _cfg(symbol))
    save_tick(conn, datetime.now() - timedelta(minutes=1), Decimal("1.10"))
    conn.close()


def test_summary_empty(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/api/portfolio/summary")
    assert r.status_code == 200
    j = r.json()
    assert j["n_instances"] == 0
    assert j["total_equity"] == "0"


def test_summary_with_instance(tmp_path: Path) -> None:
    _seed(tmp_path, "a")
    r = _client(tmp_path).get("/api/portfolio/summary")
    assert r.json()["n_instances"] == 1


def test_runners(tmp_path: Path) -> None:
    _seed(tmp_path, "a", symbol="159920")
    r = _client(tmp_path).get("/api/portfolio/runners")
    assert r.status_code == 200
    assert r.json()[0]["symbol"] == "159920"
    assert r.json()[0]["status"] == "running"


def test_watchlist_crud(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/watchlist").json() == []
    r = client.post("/api/watchlist", json={"symbol": "159920", "name": "恒生"})
    assert r.status_code == 200
    r = client.get("/api/watchlist")
    assert len(r.json()) == 1
    assert r.json()[0]["symbol"] == "159920"
    r = client.delete("/api/watchlist/159920")
    assert r.status_code == 200
    assert client.get("/api/watchlist").json() == []


def test_watchlist_remove_404(tmp_path: Path) -> None:
    r = _client(tmp_path).delete("/api/watchlist/nope")
    assert r.status_code == 404


def test_mode_isolation_and_default(tmp_path: Path) -> None:
    """?mode= query 隔离两套实例；不传 mode 默认 sim（FR-1.1 / FR-1.2）。"""
    _seed(tmp_path, "sim_inst", symbol="159920", mode="sim")
    _seed(tmp_path, "live_inst", symbol="510300", mode="live")
    client = _client(tmp_path)
    sim_runners = client.get("/api/portfolio/runners?mode=sim").json()
    live_runners = client.get("/api/portfolio/runners?mode=live").json()
    assert [r["symbol"] for r in sim_runners] == ["159920"]
    assert [r["symbol"] for r in live_runners] == ["510300"]
    # 默认（不传）= sim
    assert client.get("/api/portfolio/summary").json()["n_instances"] == 1
    # 汇总也按 mode 隔离
    assert client.get("/api/portfolio/summary?mode=sim").json()["n_instances"] == 1
    assert client.get("/api/portfolio/summary?mode=live").json()["n_instances"] == 1


def test_invalid_mode_rejected(tmp_path: Path) -> None:
    """非法 mode 被 Literal 校验拦下返 422（FR-1.2）。"""
    r = _client(tmp_path).get("/api/portfolio/runners?mode=demo")
    assert r.status_code == 422
