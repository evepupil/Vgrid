"""图 B：网格阶梯图。

把 ``LadderView`` 的档位画成横线（y=价格）：卖档（持底仓挂卖）绿、买档（现价下挂买）红、
排队档（资金上限挡下）灰虚、空闲档浅灰；现价粗线 + 资金上限标注 + 基准窗口浅带。
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from vgrid.charts._style import THEME, dec_price, kpi_strip, title_block, watermark
from vgrid.strategy.ladder_view import KIND_BUY, KIND_CAPPED, KIND_IDLE, KIND_SELL, LadderView

# 档位颜色 / 线型。
_KIND_STYLE = {
    KIND_SELL: (THEME["up"], 2.0, "-"),
    KIND_BUY: (THEME["down"], 2.0, "-"),
    KIND_CAPPED: (THEME["faint"], 1.4, (0, (4, 3))),
    KIND_IDLE: (THEME["hair"], 1.0, "-"),
}
_KIND_LABEL = {
    KIND_SELL: "卖档（持底仓）",
    KIND_BUY: "买档（挂买单）",
    KIND_CAPPED: "排队（资金上限挡）",
    KIND_IDLE: "空闲",
}


def render_ladder_chart(view: LadderView, *, symbol: str) -> Figure:
    """网格档位横线 + 现价 + 资金上限 + 基准窗口。"""
    if not view.rungs:
        raise ValueError("阶梯为空，无法画图")

    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_axes((0.18, 0.12, 0.62, 0.64))

    # 基准窗口浅带 + 放大区（窗口下沿以下）更浅带。
    ax.axhspan(float(view.window_lower), float(view.window_upper),
               color=THEME["strategy"], alpha=0.05)
    floor = min(r.price for r in view.rungs)
    if floor < view.window_lower:
        ax.axhspan(float(floor), float(view.window_lower), color=THEME["nav"], alpha=0.05)

    seen_kinds: set[str] = set()
    for rung in view.rungs:
        color, lw, ls = _KIND_STYLE[rung.kind]
        ax.hlines(float(rung.price), 0.06, 0.94, color=color, linewidth=lw, linestyle=ls)
        seen_kinds.add(rung.kind)
        # 卖档右侧标持有份额；放大区档左侧标 depth。
        if rung.kind == KIND_SELL and rung.held_shares:
            ax.text(0.96, float(rung.price), f"{dec_price(rung.price)}  {rung.held_shares}份",
                    ha="left", va="center", fontsize=8.5, color=THEME["up"])
        elif rung.depth > 0:
            ax.text(0.04, float(rung.price), f"d{rung.depth}", ha="right", va="center",
                    fontsize=7.5, color=THEME["faint"])

    # 现价粗线 + 资金上限。
    ax.axhline(float(view.current_price), color=THEME["fg"], linewidth=2.4, zorder=5)
    # 标签抬到黑线上方一点，别压在线上。
    price_span = float(view.rungs[-1].price) - float(view.rungs[0].price)
    ax.text(0.96, float(view.current_price) + price_span * 0.018,
            f"现价 {dec_price(view.current_price)}",
            ha="left", va="bottom", fontsize=10, fontweight="bold", color=THEME["fg"])
    if view.cap_price is not None:
        ax.axhline(float(view.cap_price), color=THEME["down"], linewidth=1.2,
                   linestyle=":", zorder=4)
        ax.text(0.04, float(view.cap_price), "资金上限", ha="right", va="center",
                fontsize=8.5, color=THEME["down"])

    ax.set_xlim(0, 1.35)
    ax.set_ylim(float(floor) * 0.99, float(view.rungs[-1].price) * 1.01)
    ax.set_ylabel("价格")
    ax.set_xticks([])
    ax.grid(axis="y", color=THEME["grid"], linewidth=0.7)
    ax.grid(visible=False, axis="x")

    # 右侧图例（按实际出现的档位类型）。
    handles = []
    for kind in (KIND_SELL, KIND_BUY, KIND_CAPPED, KIND_IDLE):
        if kind in seen_kinds:
            color, lw, ls = _KIND_STYLE[kind]
            handles.append(ax.plot([], [], color=color, linewidth=lw, linestyle=ls,
                                   label=_KIND_LABEL[kind])[0])
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, -0.16),
              ncol=2, fontsize=9)

    title_block(fig, "网格阶梯", f"{symbol} · {view.grid_count} 格 · {view.spacing_mode}")
    kpi_strip(fig, [
        ("窗口下沿", dec_price(view.window_lower), THEME["dim"]),
        ("窗口上沿", dec_price(view.window_upper), THEME["dim"]),
        ("格距", dec_price(view.step), THEME["dim"]),
        ("现价", dec_price(view.current_price), THEME["fg"]),
        ("资金上限价", dec_price(view.cap_price) if view.cap_price else "—", THEME["down"]),
    ])
    watermark(fig)
    return fig
