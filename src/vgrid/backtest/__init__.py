"""backtest —— 限价单撮合 + 绩效统计。复用 strategy 引擎，纯逻辑，不碰 I/O。

策略对比在 ``backtest.compare``（它同时依赖网格和定投，层级更高，故不在此 ``__init__``
里 eager 导入——否则 dca→backtest.metrics→本 __init__→compare→dca 形成循环。直接从
``vgrid.backtest.compare`` 引用）。
"""

from vgrid.backtest.matcher import simulate, simulate_with_engine
from vgrid.backtest.result import BacktestMetrics, BacktestResult, EquityPoint

__all__ = [
    "BacktestMetrics",
    "BacktestResult",
    "EquityPoint",
    "simulate",
    "simulate_with_engine",
]
