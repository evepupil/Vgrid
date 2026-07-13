"""图 E：红利增强 = 策略（价格口径）vs 分红再投增强，中间分红贡献填充。

两条曲线之间的绿色填充就是分红的累积贡献——直观量化「分红给策略加了多少」。
吃 ``ComboResult``，返回 ``Figure``。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from vgrid.charts._style import (
    THEME,
    date_axis,
    dec_cash,
    dec_pct,
    kpi_strip,
    pct_formatter,
    title_block,
    watermark,
    xdates,
)
from vgrid.income.combo import ComboResult
from vgrid.income.series import SeriesPoint

if TYPE_CHECKING:
    import numpy as np


def _xy(curve: list[SeriesPoint]) -> tuple[np.ndarray, list[float]]:
    xs = xdates([datetime(d.day.year, d.day.month, d.day.day) for d in curve])
    ys = [float(d.value) for d in curve]
    return xs, ys


def render_enhance_chart(result: ComboResult, *, symbol: str, strategy: str) -> Figure:
    """策略 vs 分红再投增强 + 分红贡献填充。"""
    if not result.strategy_curve:
        raise ValueError("增强结果为空，无法画图")

    sx, sy = _xy(result.strategy_curve)
    ex, ey = _xy(result.enhanced_curve)

    fig = plt.figure(figsize=(11, 5.8))
    ax = fig.add_axes((0.07, 0.13, 0.90, 0.63))
    ax.axhline(0, color=THEME["hair"], linewidth=0.8)
    ax.yaxis.set_major_formatter(pct_formatter(sy + ey))

    # 两线之间的分红贡献：增强≥策略处填亮绿。
    boost_mask = [b >= s for s, b in zip(sy, ey, strict=False)]
    ax.fill_between(ex, sy, ey, where=boost_mask, color=THEME["up"], alpha=0.16, linewidth=0)
    ax.plot(sx, sy, color=THEME["nav"], linewidth=1.5, linestyle="--",
            label=f"{strategy}（价格口径）")
    ax.plot(ex, ey, color=THEME["strategy"], linewidth=2.1, label="分红再投增强")

    for xs_, ys_, color, val in [
        (sx, sy, THEME["nav"], result.strategy_return),
        (ex, ey, THEME["strategy"], result.enhanced_return),
    ]:
        ax.scatter([xs_[-1]], [ys_[-1]], s=26, color=color, zorder=5)
        ax.annotate(dec_pct(val), (xs_[-1], ys_[-1]), xytext=(8, 0),
                    textcoords="offset points", fontsize=9.5, fontweight="bold",
                    color=color, va="center")

    ax.set_ylabel("累计收益率（对起始现金）")
    ax.legend(loc="upper left", ncol=2, fontsize=10)
    date_axis(ax)

    title_block(fig, "红利增强回测", f"{symbol} · {strategy}")
    kpi_strip(fig, [
        ("策略收益", dec_pct(result.strategy_return), THEME["nav"]),
        ("分红增强", dec_pct(result.enhanced_return), THEME["strategy"]),
        ("分红贡献", dec_pct(result.dividend_boost), THEME["up"]),
        ("累计到账分红", dec_cash(result.dividend_cash_total), THEME["dim"]),
        ("再投份额", f"{result.reinvest_shares}", THEME["dim"]),
    ])
    watermark(fig)
    return fig
