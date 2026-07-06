"""跑参数扫描 + 按 metric 排序。纯逻辑，复用 backtest.simulate。

每个候选 ``GridConfig`` 跑一次 ``simulate`` 取 ``metrics``（轻）；最优组合要完整报告时，
由调用方再 ``simulate`` 一次拿 ``BacktestResult``。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from vgrid.backtest.matcher import simulate
from vgrid.backtest.result import BacktestMetrics
from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig

#: 支持的排序指标（都按「越大越好」降序排）。
Metric = Literal["sharpe", "total_return", "annualized_return", "calmar"]
_METRICS: tuple[Metric, ...] = ("sharpe", "total_return", "annualized_return", "calmar")

#: 无回撤时 calmar 的占位极大值（排最前）。
_INFINITE = Decimal(10) ** 18


@dataclass(frozen=True, slots=True)
class ScanRow:
    """一组参数 + 它的回测指标。"""

    config: GridConfig
    metrics: BacktestMetrics


def run_scan(
    configs: Sequence[GridConfig],
    bars: BarSeries,
    *,
    initial_cash: Decimal | None = None,
) -> tuple[ScanRow, ...]:
    """对每组 config 跑回测，收集指标。"""
    return tuple(ScanRow(c, simulate(c, bars, initial_cash=initial_cash).metrics) for c in configs)


def metric_value(row: ScanRow, metric: Metric) -> Decimal:
    """取某行指定指标的排序值（越大越好）。

    ``calmar = 年化 / 最大回撤``；回撤为 0（从未亏损）返回极大值，排在最前。
    """
    m = row.metrics
    if metric == "sharpe":
        return m.sharpe
    if metric == "total_return":
        return m.total_return
    if metric == "annualized_return":
        return m.annualized_return
    if m.max_drawdown == 0:
        return _INFINITE
    return m.annualized_return / m.max_drawdown


def rank(rows: Sequence[ScanRow], metric: Metric) -> tuple[ScanRow, ...]:
    """按 metric 降序排（越大越好）。metric 不合法时抛 ValueError（即使 rows 为空也校验）。"""
    if metric not in _METRICS:
        raise ValueError(f"不支持的指标：{metric}；可选 {_METRICS}")
    return tuple(sorted(rows, key=lambda r: metric_value(r, metric), reverse=True))
