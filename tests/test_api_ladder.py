"""阶梯预览端点测试（纯计算，不打网、不读库）。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vgrid.core import GridConfig
from vgrid.web import create_app


def _config() -> dict[str, object]:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.10"),
        upper_price=Decimal("1.35"),
        grid_count=20,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    ).to_dict()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(strategies_dir=tmp_path))


def test_preview_ok(client: TestClient) -> None:
    r = client.post("/api/ladder/preview", json={"config": _config(), "price": "1.22"})
    assert r.status_code == 200
    j = r.json()
    assert j["current_price"] == "1.22"
    assert j["window_lower"] == "1.100"
    assert j["window_upper"] == "1.350"
    assert j["grid_count"] == 20
    assert j["spacing_mode"] == "arithmetic"
    assert len(j["rungs"]) == 21  # grid_count + 1 条网格线
    kinds = {row["kind"] for row in j["rungs"]}
    assert "sell" in kinds  # 中枢建仓在上方留下卖单格
    assert "buy" in kinds  # 下方有在挂买单


def test_preview_default_price_is_window_mid(client: TestClient) -> None:
    r = client.post("/api/ladder/preview", json={"config": _config()})
    assert r.status_code == 200
    # 缺省价 = (1.10 + 1.35) / 2 = 1.225
    assert r.json()["current_price"] == "1.225"


def test_preview_invalid_config_400(client: TestClient) -> None:
    bad = _config()
    bad["grid_count"] = 0
    r = client.post("/api/ladder/preview", json={"config": bad, "price": "1.2"})
    assert r.status_code == 400


def test_preview_invalid_price_400(client: TestClient) -> None:
    r = client.post("/api/ladder/preview", json={"config": _config(), "price": "abc"})
    assert r.status_code == 400
