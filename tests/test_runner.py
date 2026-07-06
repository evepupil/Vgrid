"""扫描排序测试（用构造的 metrics，不跑真实回测）。"""

from decimal import Decimal

import pytest

from vgrid.backtest.result import BacktestMetrics
from vgrid.core import GridConfig
from vgrid.scan.runner import ScanRow, metric_value, rank


def _cfg() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )


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


def test_calmar_zero_drawdown_ranks_first() -> None:
    rows = [_row("2.0", "0.20", "0.10"), _row("0.5", "0.05", "0.00")]
    ranked = rank(rows, "calmar")
    assert ranked[0].metrics.max_drawdown == Decimal("0")  # 无回撤排最前


def test_rank_rejects_unknown_metric() -> None:
    with pytest.raises(ValueError, match="不支持的指标"):
        rank([], "unknown")  # type: ignore[arg-type]
