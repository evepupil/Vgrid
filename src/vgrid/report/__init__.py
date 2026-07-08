"""report —— 绩效报告渲染（Markdown + 终端摘要）。纯展示层。"""

from vgrid.report.compare import render_comparison, render_comparison_report
from vgrid.report.dca import render_dca_report, render_dca_summary
from vgrid.report.markdown import render_report
from vgrid.report.terminal import render_summary

__all__ = [
    "render_comparison",
    "render_comparison_report",
    "render_dca_report",
    "render_dca_summary",
    "render_report",
    "render_summary",
]
