"""图 C：三方对比 = 网格 / 定投 / 买入持有 净值叠加。

同一笔起始现金、同一段行情，把每条策略的逐 K 权益归一成累计收益率叠在一张图上，
末点标收益。吃 ``StrategyComparison``，返回 ``Figure``。
"""

from __future__ import annotations

from decimal import Decimal

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from vgrid.backtest.compare import StrategyComparison
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


def _color_for(name: str) -> tuple[str, str]:
    """策略名 → (线色, 末点标签色)。网格蓝 / 定投青 / 买入持有灰。"""
    if "网格" in name:
        return THEME["strategy"], THEME["strategy"]
    if "定投" in name:
        return THEME["reinvest"], THEME["reinvest"]
    if "买入持有" in name:
        return THEME["buy_hold"], THEME["faint"]
    return THEME["accent2"], THEME["accent2"]


def render_compare_chart(comparison: StrategyComparison) -> Figure:
    """三方（或多策略）净值叠加 + 末点收益标注。"""
    rows = comparison.rows
    bars = comparison.bars
    if not rows or not bars:
        raise ValueError("对比结果为空，无法画图")
    initial = comparison.initial_cash

    fig = plt.figure(figsize=(11, 5.8))
    ax = fig.add_axes((0.07, 0.13, 0.90, 0.63))
    ax.axhline(0, color=THEME["hair"], linewidth=0.8)

    end_ts = bars[-1].ts
    kpi_items = []
    all_ret: list[float] = []
    for r in rows:
        if not r.curve:
            continue
        xs = xdates([p.ts for p in r.curve])
        ret = [float(p.equity / initial - 1) for p in r.curve]
        all_ret.extend(ret)
        color, _ = _color_for(r.name)
        ax.plot(xs, ret, color=color, linewidth=1.9, label=r.name)
        ax.scatter([xs[-1]], [ret[-1]], s=28, color=color, zorder=5)
        ax.annotate(dec_pct(r.total_return), (xs[-1], ret[-1]),
                    xytext=(8, 0), textcoords="offset points", fontsize=9.5,
                    fontweight="bold", color=color, va="center")
        kpi_items.append((r.name, dec_pct(r.total_return), color))

    ax.yaxis.set_major_formatter(pct_formatter(all_ret))
    ax.set_ylabel("累计收益率（对起始现金）")
    ax.legend(loc="upper left", ncol=len(rows), fontsize=10)
    date_axis(ax)
    ax.set_xlim(xdates([bars[0].ts])[0], xdates([end_ts])[0])

    start, end = bars[0].ts.date(), bars[-1].ts.date()
    title_block(fig, "策略对比", f"起始现金 ¥{Decimal(comparison.initial_cash):,} · "
                               f"{start} → {end} · {len(bars)} 根")
    kpi_strip(fig, kpi_items)
    watermark(fig)
    return fig
