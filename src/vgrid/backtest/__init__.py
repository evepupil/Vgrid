"""backtest —— 限价单撮合 + 绩效统计。复用 strategy 引擎，纯逻辑，不碰 I/O。"""

from vgrid.backtest.matcher import simulate
from vgrid.backtest.result import BacktestMetrics, BacktestResult, EquityPoint

__all__ = [
    "BacktestMetrics",
    "BacktestResult",
    "EquityPoint",
    "simulate",
]
