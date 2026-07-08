"""scan_api 测试：spec 展开 → 逐组回测 → top-N 排序 + JSON 安全序列化。"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.scan import ScanSpec
from vgrid.scan.runner import Metric
from vgrid.web.scan_api import run_scan_api


def _run_scan_api(metric: Metric, top: int) -> dict[str, Any]:
    return cast(dict[str, Any], run_scan_api(_spec(), _bars(), metric=metric, top=top))


def _bars(n: int = 80) -> BarSeries:
    """正弦波日线，穿网格来回，好让不同格数产出不同指标。"""
    bars = []
    for i in range(n):
        px = 1.10 + 0.06 * math.sin(i / 2.0)
        c = Decimal(str(round(px, 4)))
        half = Decimal(str(round(px * 0.015, 4)))
        bars.append(
            Bar(
                ts=datetime(2024, 1, 1) + timedelta(days=i),
                open=c,
                high=c + half,
                low=c - half,
                close=c,
                volume=Decimal("100"),
            )
        )
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=tuple(bars))


def _spec() -> ScanSpec:
    return ScanSpec(
        fixed={
            "symbol": "159920",
            "lower_price": "1.00",
            "upper_price": "1.20",
            "per_grid_amount": "2000",
            "capital_cap": "50000",
        },
        vary={"grid_count": [4, 6, 8]},
    )


def test_scan_structure() -> None:
    d = _run_scan_api(metric="sharpe", top=10)
    assert d["metric"] == "sharpe"
    assert d["total"] == 3  # 3 个格数
    assert d["shown"] == 3
    assert d["vary_keys"] == ["grid_count"]
    assert isinstance(d["rows"], list) and len(d["rows"]) == 3
    assert "样本内" in str(d["overfit_note"])


def test_scan_row_serialisation() -> None:
    row = _run_scan_api(metric="sharpe", top=1)["rows"][0]
    assert set(row["params"]) == {"grid_count"}
    assert isinstance(row["params"]["grid_count"], int)
    m = row["metrics"]
    for key in ("sharpe", "total_return", "annualized_return", "max_drawdown", "final_equity"):
        assert isinstance(m[key], str)
    assert isinstance(m["n_buys"], int)


def test_scan_sorted_desc_by_metric() -> None:
    d = _run_scan_api(metric="total_return", top=10)
    returns = [Decimal(r["metrics"]["total_return"]) for r in d["rows"]]
    assert returns == sorted(returns, reverse=True)


def test_scan_top_clamps() -> None:
    d = _run_scan_api(metric="sharpe", top=2)
    assert d["total"] == 3  # 扫了 3 组
    assert d["shown"] == 2  # 只回前 2
    assert len(d["rows"]) == 2
