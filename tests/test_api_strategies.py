"""策略库 API 端点测试（TestClient + tmp_path 策略目录）。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from vgrid.core.config import GridConfig
from vgrid.web import create_app


def _client(tmp_path: Path) -> TestClient:
    # data_dir 也指到 tmp_path，部署 / 实例检测都在临时目录内，测试互不干扰。
    return TestClient(create_app(strategies_dir=tmp_path, data_dir=tmp_path))


def _config() -> dict[str, object]:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.976"),
        upper_price=Decimal("1.024"),
        grid_count=16,
        per_grid_amount=Decimal("3000"),
        capital_cap=Decimal("50000"),
    ).to_dict()


def test_list_empty(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/api/strategies")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post("/api/strategies", json={"name": "恒生网格", "config": _config()})
    assert r.status_code == 200
    assert r.json()["symbol"] == "159920"
    r = client.get("/api/strategies/恒生网格")
    assert r.status_code == 200
    assert r.json()["grid_count"] == 16


def test_list_returns_summary(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post("/api/strategies", json={"name": "a", "config": _config()})
    r = client.get("/api/strategies")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "a"
    assert r.json()[0]["symbol"] == "159920"


def test_get_404(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/api/strategies/nope")
    assert r.status_code == 404


def test_create_invalid_config_400(tmp_path: Path) -> None:
    bad = _config()
    bad["grid_count"] = 0
    r = _client(tmp_path).post("/api/strategies", json={"name": "bad", "config": bad})
    assert r.status_code == 400


def test_create_invalid_name_400(tmp_path: Path) -> None:
    r = _client(tmp_path).post("/api/strategies", json={"name": "../etc", "config": _config()})
    assert r.status_code == 400


def test_put_updates(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post("/api/strategies", json={"name": "a", "config": _config()})
    cfg = _config()
    cfg["grid_count"] = 32
    r = client.put("/api/strategies/a", json=cfg)
    assert r.status_code == 200
    assert r.json()["grid_count"] == 32


def test_put_rejected_when_deployed(tmp_path: Path) -> None:
    """已部署成实例的策略改配置被拒 409（review #25），配置不被改。"""
    client = _client(tmp_path)
    client.post("/api/strategies", json={"name": "a", "config": _config()})
    assert client.post("/api/strategies/a/deploy", json={"mode": "sim"}).status_code == 200

    cfg = _config()
    cfg["grid_count"] = 32
    r = client.put("/api/strategies/a", json=cfg)
    assert r.status_code == 409
    assert "先停" in r.json()["detail"]
    assert client.get("/api/strategies/a").json()["grid_count"] == 16


def test_delete(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post("/api/strategies", json={"name": "a", "config": _config()})
    r = client.delete("/api/strategies/a")
    assert r.status_code == 200
    assert client.get("/api/strategies/a").status_code == 404
