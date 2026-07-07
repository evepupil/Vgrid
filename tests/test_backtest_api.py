"""backtest_api 纯逻辑测试（不碰网络，构造 BarSeries 直接跑）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.web.backtest_api import run_backtest


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
            _bar(3, "1.04", "1.07", "1.01", "1.05"),
        ),
    )


def _cfg() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.90"),
        upper_price=Decimal("1.20"),
        grid_count=6,
        per_grid_amount=Decimal("3000"),
        capital_cap=Decimal("50000"),
    )


def test_run_backtest_structure() -> None:
    d = run_backtest(_bars(), _cfg())
    assert "metrics" in d
    assert "equity_curve" in d
    assert "fills" in d
    assert d["n_bars"] == 3
    assert isinstance(d["equity_curve"], list)
    assert len(d["equity_curve"]) == 3  # 3 <= 500，不降采样


def test_metrics_are_strings() -> None:
    result = run_backtest(_bars(), _cfg())
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert isinstance(metrics["total_return"], str)
    assert isinstance(metrics["max_drawdown"], str)
    assert isinstance(metrics["sharpe"], str)
    assert isinstance(metrics["n_buys"], int)
    assert isinstance(metrics["n_sells"], int)


def test_curve_downsampled_when_large() -> None:
    bars = BarSeries(
        symbol="159920",
        frame=Frame.DAILY,
        bars=tuple(_bar(d, "1.00", "1.01", "0.99", "1.005") for d in range(500)),
    )
    result = run_backtest(bars, _cfg())
    curve = result["equity_curve"]
    assert isinstance(curve, list)
    assert 1 < len(curve) <= 500


def test_empty_bars_raises() -> None:
    empty = BarSeries(symbol="159920", frame=Frame.DAILY, bars=())
    with pytest.raises(ValueError):
        run_backtest(empty, _cfg())


def test_result_has_drawdown_and_buyhold_curves() -> None:
    # FR-7.3：回撤 + 买入持有对照序列，与 equity_curve 同点
    result = run_backtest(_bars(), _cfg())
    eq = result["equity_curve"]
    dd = result["drawdown_curve"]
    bh = result["buy_hold_curve"]
    assert isinstance(eq, list) and isinstance(dd, list) and isinstance(bh, list)
    assert len(dd) == len(eq) == len(bh)
    assert all(isinstance(p["drawdown"], str) for p in dd)
    assert all(isinstance(p["equity"], str) for p in bh)
    # 回撤恒 ≤ 0
    assert all(Decimal(p["drawdown"]) <= 0 for p in dd)


def test_result_has_end_ladder_and_overfit_note() -> None:
    # FR-7.4 期末阶梯 + FR-7.5 过拟合提示
    result = run_backtest(_bars(), _cfg())
    ladder = result["end_ladder"]
    assert isinstance(ladder, dict)
    assert "rungs" in ladder and isinstance(ladder["rungs"], list)
    assert isinstance(result["overfit_note"], str)
    assert "样本内" in str(result["overfit_note"])


def test_end_ladder_can_be_skipped() -> None:
    result = run_backtest(_bars(), _cfg(), include_ladder=False)
    assert result["end_ladder"] is None
