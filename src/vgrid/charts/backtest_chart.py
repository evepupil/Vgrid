"""图 A：回测主图 = 净值（策略 vs 买入持有 + 买卖点）+ 回撤水下条。

上大下小双面板、共享 x 轴：上面是累计收益率（策略蓝实线 + 买入持有灰虚线，买卖点用
绿▲/红▼标在策略线上），下面是策略回撤（红填充）。顶部一行 KPI（收益 / 年化 / 回撤 / 夏普 /
手续费）。吃 ``BacktestResult``，返回 ``Figure``。
"""

from __future__ import annotations

from decimal import Decimal

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from vgrid.backtest.result import BacktestResult
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
from vgrid.core.enums import Side


def render_backtest_chart(result: BacktestResult, *, symbol: str) -> Figure:
    """策略净值 vs 买入持有 + 买卖点 + 回撤。"""
    eq = result.equity_curve
    bars = result.bars
    m = result.metrics
    if not eq or not bars:
        raise ValueError("回测结果为空，无法画图")

    initial = m.initial_cash
    xs = xdates([p.ts for p in eq])
    strat = [float(p.equity / initial - 1) for p in eq]

    # 买入持有：首日满仓（分数份额，纯基准曲线），与策略同 x。
    first_close = bars[0].close
    bh_shares = initial / first_close
    bh = [float(bh_shares * bar.close / initial - 1) for bar in bars]

    # 策略回撤（按权益峰值）。
    peak = eq[0].equity
    dd = []
    for p in eq:
        peak = max(peak, p.equity)
        dd.append(float(p.equity / peak - 1) if peak > 0 else 0.0)

    ts_to_idx = {p.ts: i for i, p in enumerate(eq)}
    buys = [(f.ts, strat[ts_to_idx[f.ts]]) for f in result.fills
            if f.ts is not None and f.side is Side.BUY and f.ts in ts_to_idx]
    sells = [(f.ts, strat[ts_to_idx[f.ts]]) for f in result.fills
             if f.ts is not None and f.side is Side.SELL and f.ts in ts_to_idx]

    fig = plt.figure(figsize=(11, 6.2))
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08,
                  left=0.07, right=0.97, top=0.78, bottom=0.09)
    ax = fig.add_subplot(gs[0])
    axd = fig.add_subplot(gs[1], sharex=ax)

    # 上：策略净值（蓝实 + 浅填充）+ 买入持有（灰虚）+ 买卖点。
    ax.axhline(0, color=THEME["hair"], linewidth=0.8)
    ax.fill_between(xs, 0, strat, color=THEME["strategy"], alpha=0.07)
    ax.plot(xs, strat, color=THEME["strategy"], linewidth=1.8, label="策略净值")
    ax.plot(xs, bh, color=THEME["buy_hold"], linewidth=1.3, linestyle="--", label="买入持有")
    if buys:
        bxs, bys = zip(*buys, strict=False)
        ax.scatter(xdates(bxs), bys, marker="^", s=22, color=THEME["up"], zorder=5, label="买")
    if sells:
        sxs, sys_ = zip(*sells, strict=False)
        ax.scatter(xdates(sxs), sys_, marker="v", s=22, color=THEME["down"], zorder=5, label="卖")
    ax.yaxis.set_major_formatter(pct_formatter(strat + bh))
    ax.set_ylabel("累计收益率")
    ax.legend(loc="upper left", ncol=4, fontsize=9.5)
    plt.setp(ax.get_xticklabels(), visible=False)

    # 下：回撤水下条（红填充到 0）。
    axd.axhline(0, color=THEME["hair"], linewidth=0.8)
    axd.fill_between(xs, dd, 0, color=THEME["down"], alpha=0.25)
    axd.plot(xs, dd, color=THEME["down"], linewidth=1.0)
    axd.yaxis.set_major_formatter(pct_formatter(dd))
    axd.set_ylabel("回撤")
    date_axis(axd)

    start, end = bars[0].ts.date(), bars[-1].ts.date()
    title_block(fig, "网格回测", f"{symbol} · {start} → {end} · {len(bars)} 根")
    kpi_strip(fig, [
        ("累计收益", dec_pct(m.total_return), THEME["strategy"]),
        ("年化", dec_pct(m.annualized_return), THEME["fg"]),
        ("最大回撤", dec_pct(m.max_drawdown * Decimal(-1)), THEME["down"]),
        ("夏普", f"{float(m.sharpe):.2f}", THEME["fg"]),
        ("手续费", f"¥{float(m.total_fee):,.0f}", THEME["dim"]),
        ("买卖笔数", f"{m.n_buys}买 / {m.n_sells}卖", THEME["dim"]),
    ])
    watermark(fig)
    return fig
