"""income 对比 API 端点测试（mock build_comparison，不打网）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from vgrid.web import create_app


def _curve(n: int = 50) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(day=date(2024, 1, 1 + i % 28), value=Decimal("0.01") * i) for i in range(n)
    ]


def _metrics(annualized: str) -> SimpleNamespace:
    return SimpleNamespace(
        sample_start=date(2024, 1, 1),
        sample_end=date(2025, 1, 1),
        price_return=Decimal("0.05"),
        cash_dividend_return=Decimal("0.07"),
        reinvest_return=Decimal("0.08"),
        acc_nav_return=Decimal("0.085"),
        annualized_return=Decimal(annualized),
        max_drawdown=Decimal("0.15"),
        n_dividends=2,
        sample_per_share=Decimal("0.3"),
        sample_dividend_yield=Decimal("0.04"),
        ttm_dividend_yield=Decimal("0.045"),
        total_expense_rate=Decimal("0.006"),
        data_quality=SimpleNamespace(value="ok"),
        warnings=(),
    )


def _result(code: str, name: str, annualized: str) -> SimpleNamespace:
    return SimpleNamespace(
        code=code,
        name=name,
        inception=date(2020, 1, 1),
        metrics=_metrics(annualized),
        price_curve=_curve(),
        cash_dividend_curve=_curve(),
        reinvest_curve=_curve(),
        acc_nav_curve=_curve(),
    )


def _fake_run() -> SimpleNamespace:
    return SimpleNamespace(
        pool_size=3,
        skipped=["999999"],
        spec=SimpleNamespace(
            initial_cash=Decimal("100000"), start=date(2024, 1, 1), end=date(2025, 1, 1)
        ),
        comparison=SimpleNamespace(
            results=[_result("510880", "红利ETF", "0.12"), _result("515180", "红利低波", "0.10")],
            sort_keys=("annualized", "drawdown", "ttm_yield", "expense"),
        ),
    )


def test_income_compare_ranking_and_curves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vgrid.web.income_api.build_comparison", lambda spec: _fake_run())
    client = TestClient(create_app())
    r = client.post(
        "/api/income/compare",
        json={"start": "2024-01-01", "end": "2025-01-01", "keywords": ["红利"]},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["pool_size"] == 3
    assert j["skipped"] == ["999999"]
    assert j["rows"][0]["code"] == "510880"  # build_comparison 已排好序，原样返回
    row = j["rows"][0]
    assert set(row["curves"]) == {"price", "cash_dividend", "reinvest", "acc_nav"}
    assert row["metrics"]["data_quality"] == "ok"
    assert len(row["curves"]["price"]) <= 100  # 降采样上限


def test_income_compare_invalid_cash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vgrid.web.income_api.build_comparison", lambda spec: _fake_run())
    client = TestClient(create_app())
    r = client.post(
        "/api/income/compare",
        json={"start": "2024-01-01", "end": "2025-01-01", "initial_cash": "abc"},
    )
    assert r.status_code == 400


def _fake_combo() -> SimpleNamespace:
    return SimpleNamespace(
        strategy_return=Decimal("0.1179"),
        enhanced_return=Decimal("0.1868"),
        dividend_boost=Decimal("0.0689"),
        dividend_cash_total=Decimal("6003.40"),
        reinvest_shares=1900,
        strategy_curve=_curve(),
        enhanced_curve=_curve(),
    )


def test_income_enhance_returns_two_curves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vgrid.web.income_api.build_enhance", lambda **kw: _fake_combo()
    )
    client = TestClient(create_app())
    r = client.post(
        "/api/income/enhance",
        json={
            "symbol": "510880",
            "start": "2021-01-01",
            "end": "2024-12-31",
            "strategy": "dca",
            "config": {"symbol": "510880"},
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j["dividend_boost"] == "0.0689"
    assert j["reinvest_shares"] == 1900
    assert len(j["strategy_curve"]) <= 300
    assert len(j["enhanced_curve"]) == len(j["strategy_curve"])


def test_income_enhance_rejects_bad_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    r = TestClient(create_app()).post(
        "/api/income/enhance",
        json={
            "symbol": "510880",
            "start": "2021-01-01",
            "end": "2024-12-31",
            "strategy": "bogus",
            "config": {},
        },
    )
    assert r.status_code == 422  # Literal 校验挡下
