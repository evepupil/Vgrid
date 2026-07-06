"""report —— 绩效报告渲染（Markdown + 终端摘要）。纯展示层。"""

from vgrid.report.markdown import render_report
from vgrid.report.terminal import render_summary

__all__ = [
    "render_report",
    "render_summary",
]
