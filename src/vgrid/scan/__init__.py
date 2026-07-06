"""scan —— 参数扫描（网格搜索）。复用 backtest.simulate，纯逻辑 + 渲染。"""

from vgrid.scan.markdown import render_scan_report
from vgrid.scan.runner import ScanRow, metric_value, rank, run_scan
from vgrid.scan.space import ScanSpec

__all__ = [
    "ScanRow",
    "ScanSpec",
    "metric_value",
    "rank",
    "render_scan_report",
    "run_scan",
]
