"""charts —— 把回测数据画成可分享的静态图（知乎友好，白底专业风）。

每类图一个文件，共用 ``_style`` 的配色 / 字体 / 标题 / 水印骨架。纯消费现有结果对象
（``BacktestResult`` / ``LadderView`` / ``StrategyComparison`` / ``EtfIncomeResult`` /
``ComboResult`` / 扫描结果），不改回测逻辑。图函数返回 ``matplotlib.figure.Figure``，
由调用方 ``save_png`` 落盘。
"""

from vgrid.charts._style import (
    THEME,
    apply_theme,
    date_axis,
    dec_cash,
    dec_pct,
    dec_price,
    kpi_strip,
    pct_formatter,
    save_png,
    title_block,
    watermark,
    xdates,
)
from vgrid.charts.backtest_chart import render_backtest_chart
from vgrid.charts.compare_chart import render_compare_chart
from vgrid.charts.enhance_chart import render_enhance_chart
from vgrid.charts.income_chart import render_income_chart
from vgrid.charts.ladder_chart import render_ladder_chart
from vgrid.charts.scan_chart import render_scan_heatmap

__all__ = [
    "THEME",
    "apply_theme",
    "date_axis",
    "dec_cash",
    "dec_pct",
    "dec_price",
    "kpi_strip",
    "pct_formatter",
    "render_backtest_chart",
    "render_compare_chart",
    "render_enhance_chart",
    "render_income_chart",
    "render_ladder_chart",
    "render_scan_heatmap",
    "save_png",
    "title_block",
    "watermark",
    "xdates",
]

