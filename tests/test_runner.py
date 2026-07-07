"""扫描排序测试（排序用构造的 metrics；run_scan 主路径用小 bars 真跑一遍）。"""

from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.backtest.result import BacktestMetrics
from vgrid.core import GridConfig
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.scan.runner import ScanRow, metric_value, rank, run_scan


def _cfg(grid_count: int = 4) -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=grid_count,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )


def _bars() -> BarSeries:
    prices = ["1.10", "1.05", "1.00", "1.08", "1.15"]
    bars = tuple(
        Bar(
            ts=datetime(2024, 1, i + 1),
            open=Decimal(p),
            high=Decimal(p),
            low=Decimal(p),
            close=Decimal(p),
            volume=Decimal("1000"),
        )
        for i, p in enumerate(prices)
    )
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=bars)


def _row(sharpe: str, ann: str, dd: str, total: str = "0.1") -> ScanRow:
    m = BacktestMetrics(
        initial_cash=Decimal("100"),
        final_equity=Decimal("100"),
        total_return=Decimal(total),
        annualized_return=Decimal(ann),
        max_drawdown=Decimal(dd),
        sharpe=Decimal(sharpe),
        win_rate=Decimal("1"),
        profit_loss_ratio=Decimal("0"),
        n_buys=0,
        n_sells=0,
        total_fee=Decimal("0"),
        buy_hold_return=Decimal("0"),
    )
    return ScanRow(_cfg(), m)


def test_rank_by_sharpe_descending() -> None:
    rows = [_row("1.0", "0.10", "0.05"), _row("2.0", "0.05", "0.02"), _row("0.5", "0.20", "0.10")]
    ranked = rank(rows, "sharpe")
    assert [r.metrics.sharpe for r in ranked] == [
        Decimal("2.0"),
        Decimal("1.0"),
        Decimal("0.5"),
    ]


def test_rank_by_calmar() -> None:
    # calmar = 年化 / 最大回撤：0.10/0.05=2.0，0.12/0.04=3.0 → 后者排前
    rows = [_row("1", "0.10", "0.05"), _row("1", "0.12", "0.04")]
    ranked = rank(rows, "calmar")
    assert ranked[0].metrics.annualized_return == Decimal("0.12")
    assert metric_value(ranked[0], "calmar") == Decimal("0.12") / Decimal("0.04")
    assert metric_value(ranked[1], "calmar") == Decimal("0.10") / Decimal("0.05")


def test_calmar_zero_drawdown_but_profitable_ranks_first() -> None:
    # 无回撤且赚了钱（年化 0.05 > 0）→ 确实优秀，给极大值排最前
    rows = [_row("2.0", "0.20", "0.10"), _row("0.5", "0.05", "0.00")]
    ranked = rank(rows, "calmar")
    assert ranked[0].metrics.max_drawdown == Decimal("0")


def test_calmar_flat_config_does_not_rank_above_real_one() -> None:
    """回归 #14：躺平配置（没交易、权益直线 → 年化 0、回撤 0）不再刷成极大值排第一。"""
    flat = _row("0", "0.00", "0.00")  # 没赚钱、没回撤
    real = _row("1.5", "0.20", "0.10")  # 真赚了钱、有回撤
    ranked = rank([flat, real], "calmar")
    assert ranked[0] is real
    assert metric_value(flat, "calmar") == Decimal("0")  # 不再是 10^18


def test_run_scan_collects_metrics_and_reports_progress() -> None:
    """回归 #18：run_scan 主路径真跑一遍，每组拿到 metrics，进度回调按序触发。"""
    configs = (_cfg(grid_count=4), _cfg(grid_count=6))
    seen: list[tuple[int, int]] = []
    rows = run_scan(configs, _bars(), progress=lambda done, total: seen.append((done, total)))

    assert len(rows) == 2
    assert all(isinstance(r.metrics, BacktestMetrics) for r in rows)
    assert [r.config.grid_count for r in rows] == [4, 6]
    assert seen == [(1, 2), (2, 2)]


def test_rank_rejects_unknown_metric() -> None:
    with pytest.raises(ValueError, match="不支持的指标"):
        rank([], "unknown")  # type: ignore[arg-type]
