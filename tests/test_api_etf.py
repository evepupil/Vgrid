"""ETF 信息 API 测试（mock get_etf_name 不打网）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vgrid.web import create_app


def test_etf_info_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vgrid.web.routes.etf.get_etf_name",
        lambda s: "恒生ETF" if s == "159920" else None,
    )
    client = TestClient(create_app())
    r = client.get("/api/etf/159920/info")
    assert r.status_code == 200
    assert r.json() == {"symbol": "159920", "name": "恒生ETF"}


def test_etf_info_not_found_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vgrid.web.routes.etf.get_etf_name", lambda s: None)
    client = TestClient(create_app())
    r = client.get("/api/etf/000000/info")
    assert r.status_code == 404
