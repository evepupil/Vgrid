"""图 G：多标的批量回测排名——每只 ETF 一行，定投 XIRR vs 一次性买入收益率横向分组条。

按排序键从上到下排名（最好的在上）。青条=定投 XIRR，灰条=同期一次性买入。吃 ``BatchResult``。
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.pyplot import figure

from vgrid.batch.models import BatchResult
from vgrid.charts._style import (
    THEME,
    dec_pct,
    kpi_strip,
    pct_formatter,
    title_block,
    watermark,
)

_BAR_H = 0.38  # 单条高度（两条一组，组内错开）


def render_batch_chart(result: BatchResult, *, title: str = "批量回测排名") -> Figure:
    """定投 XIRR vs 一次性买入 横向分组条，按排名排列。"""
    rows = [r for r in result.ok_rows if r.dca_xirr is not None or r.buy_hold_return is not None]
    if not rows:
        raise ValueError("没有可画的批量结果（全部跳过或无指标）")

    labels = [f"{r.name}\n{r.code}" for r in rows]
    dca = [float(r.dca_xirr) if r.dca_xirr is not None else 0.0 for r in rows]
    bh = [float(r.buy_hold_return) if r.buy_hold_return is not None else 0.0 for r in rows]

    # y 轴从上到下 = 排名从好到差：最好的排最上，故 y 逆序。
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)

    fig = figure(figsize=(10, max(3.2, 0.62 * n + 2.4)))
    ax = fig.add_axes((0.20, 0.10, 0.72, 0.66))
    ax.axvline(0, color=THEME["hair"], linewidth=0.8)

    ax.barh(y + _BAR_H / 2, dca, height=_BAR_H, color=THEME["reinvest"], label="定投 XIRR")
    ax.barh(y - _BAR_H / 2, bh, height=_BAR_H, color=THEME["buy_hold"], label="一次性买入收益率")

    # 每条末端标数值。
    span = max(dca + bh + [0.0]) - min(dca + bh + [0.0]) or 1.0
    for yi, dv, bv in zip(y, dca, bh, strict=True):
        _bar_label(ax, dv, yi + _BAR_H / 2, span, THEME["reinvest"])
        _bar_label(ax, bv, yi - _BAR_H / 2, span, THEME["buy_hold"])

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.xaxis.set_major_formatter(pct_formatter(dca + bh))
    ax.set_xlabel("年化 / 收益率")
    ax.legend(loc="lower right", ncol=2, fontsize=9)
    ax.grid(visible=False, axis="y")

    best = rows[0]
    title_block(fig, title, f"{result.start} ~ {result.end} · {len(rows)} 只 · 按排名")
    kpi_strip(fig, [
        ("上榜", str(len(rows)), THEME["dim"]),
        ("榜首", best.name, THEME["strategy"]),
        ("榜首定投XIRR", dec_pct(best.dca_xirr), THEME["reinvest"]),
        ("榜首一次性", dec_pct(best.buy_hold_return), THEME["buy_hold"]),
    ])
    watermark(fig)
    return fig


def _bar_label(ax: Axes, value: float, y: float, span: float, color: str) -> None:
    """条末端标百分比：正值标右、负值标左。"""
    off = span * 0.012
    ha = "left" if value >= 0 else "right"
    ax.text(value + (off if value >= 0 else -off), y, f"{value * 100:.1f}%",
            ha=ha, va="center", fontsize=8.5, color=color)
