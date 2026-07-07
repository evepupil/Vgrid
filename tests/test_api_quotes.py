"""报价端点测试（注入 stub provider，不打网）。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vgrid.web import create_app
from vgrid.web.quotes import Quote


class StubProvider:
    """按代码返回固定报价，未知代码不返回（模拟现货表过滤）。"""

    def fetch_many(self, symbols: list[str]) -> list[Quote]:
        table = {
            "159920": Quote("159920", "恒生 ETF", Decimal("1.246"), Decimal("1.229"),
                            Decimal("0.017"), Decimal("1.38")),
            "513100": Quote("513100", "纳指 ETF", Decimal("1.512"), Decimal("1.519"),
                            Decimal("-0.007"), Decimal("-0.46")),
        }
        return [table[s] for s in symbols if s in table]


class BoomProvider:
    """模拟行情源故障。"""

    def fetch_many(self, symbols: list[str]) -> list[Quote]:
        raise RuntimeError("网络不可用")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(strategies_dir=tmp_path, quote_provider=StubProvider()))


def test_quotes_ok(client: TestClient) -> None:
    r = client.get("/api/quotes", params={"symbols": "159920,513100"})
    assert r.status_code == 200
    j = r.json()
    assert j["error"] is None
    assert len(j["quotes"]) == 2
    first = j["quotes"][0]
    assert first["symbol"] == "159920"
    assert first["price"] == "1.246"
    assert first["prev_close"] == "1.229"
    assert first["change_pct"] == "1.38"


def test_quotes_preserves_order_and_skips_unknown(client: TestClient) -> None:
    r = client.get("/api/quotes", params={"symbols": "999999,513100,159920"})
    codes = [q["symbol"] for q in r.json()["quotes"]]
    assert codes == ["513100", "159920"]  # 未知 999999 跳过，其余保序


def test_quotes_empty_symbols(client: TestClient) -> None:
    r = client.get("/api/quotes", params={"symbols": ""})
    assert r.status_code == 200
    assert r.json()["quotes"] == []


def test_quotes_source_failure_degrades(tmp_path: Path) -> None:
    client = TestClient(create_app(strategies_dir=tmp_path, quote_provider=BoomProvider()))
    r = client.get("/api/quotes", params={"symbols": "159920"})
    assert r.status_code == 200  # 不崩
    j = r.json()
    assert j["quotes"] == []
    assert j["error"] is not None
