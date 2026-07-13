"""图 D：红利 ETF 四口径收益曲线叠加。

价格 / 价格+现金分红 / 价格+分红再投 / 累计净值，四条都起点归零，叠在一张图。再投是主口径
（年化排名用它），画粗一些；累计净值是校验基准，画灰点线。吃 ``EtfIncomeResult``。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from vgrid.charts._style import (
    THEME,
    date_axis,
    dec_pct,
    kpi_strip,
    pct_formatter,
    title_block,
    watermark,
    xdates,
)
from vgrid.income.report import EtfIncomeResult
from vgrid.income.series import SeriesPoint

if TYPE_CHECKING:
    import numpy as np


def _xy(curve: list[SeriesPoint]) -> tuple[np.ndarray, list[float]]:
    xs = xdates([datetime(d.day.year, d.day.month, d.day.day) for d in curve])
    ys = [float(d.value) for d in curve]
    return xs, ys


def render_income_chart(result: EtfIncomeResult) -> Figure:
    """红利 ETF 四口径收益叠加 + 分红率标注。"""
    m = result.metrics
    if not result.price_curve:
        raise ValueError(f"{result.code} 无价格曲线，无法画图")

    fig = plt.figure(figsize=(11, 5.8))
    ax = fig.add_axes((0.07, 0.13, 0.90, 0.63))
    ax.axhline(0, color=THEME["hair"], linewidth=0.8)

    px, py = _xy(result.price_curve)
    cx, cy = _xy(result.cash_dividend_curve)
    rx, ry = _xy(result.reinvest_curve)
    ax.yaxis.set_major_formatter(pct_formatter(py + ry))
    ax.plot(px, py, color=THEME["strategy"], linewidth=1.5, label="价格")
    ax.plot(cx, cy, color=THEME["accent2"], linewidth=1.5, linestyle="--", label="价格 + 现金分红")
    ax.plot(rx, ry, color=THEME["up"], linewidth=2.1, label="价格 + 分红再投")  # 主口径
    if result.acc_nav_curve:
        nx, ny = _xy(result.acc_nav_curve)
        ax.plot(nx, ny, color=THEME["nav"], linewidth=1.2, linestyle=(0, (1, 3)),
                label="累计净值")

    # 末点收益标注（再投口径）。
    ax.scatter([rx[-1]], [ry[-1]], s=28, color=THEME["up"], zorder=5)
    ax.annotate(dec_pct(m.reinvest_return), (rx[-1], ry[-1]), xytext=(8, 0),
                textcoords="offset points", fontsize=9.5, fontweight="bold",
                color=THEME["up"], va="center")

    ax.set_ylabel("累计收益率（起点归零）")
    ax.legend(loc="upper left", ncol=4, fontsize=9.5)
    date_axis(ax)

    title_block(fig, f"红利收益对比 · {result.code} {result.name}",
                f"{m.sample_start} → {m.sample_end} · 分红 {m.n_dividends} 次")
    kpi_strip(fig, [
        ("价格收益", dec_pct(m.price_return), THEME["strategy"]),
        ("现金分红", dec_pct(m.cash_dividend_return), THEME["accent2"]),
        ("分红再投", dec_pct(m.reinvest_return), THEME["up"]),
        ("累计净值", dec_pct(m.acc_nav_return), THEME["nav"]),
        ("样本分红率", dec_pct(m.sample_dividend_yield), THEME["dim"]),
        ("近12月分红率", dec_pct(m.ttm_dividend_yield), THEME["dim"]),
    ])
    watermark(fig)
    return fig
