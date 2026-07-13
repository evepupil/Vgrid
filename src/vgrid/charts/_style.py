"""分享图样式系统：白底专业风（知乎友好），全 charts 模块共用。

一套配色 + 微软雅黑 + 统一的「标题 / 副标题 / KPI 行 / 水印」骨架。每张图函数自己组装 axes，
这里只给色板和排版 helper。import 即生效（``apply_theme`` 设 rcParams），幂等。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# 白底专业配色：策略净值=深蓝主色，买入持有=灰，回撤/卖=红，买=绿。
THEME: dict[str, str] = {
    "bg": "#ffffff",
    "panel": "#ffffff",
    "fg": "#1a1f2c",  # 主文字（深墨）
    "dim": "#5b6573",  # 次文字 / 轴标签
    "faint": "#9aa3ad",  # 弱文字 / 网格基线
    "grid": "#eef0f3",  # 浅网格
    "hair": "#d8dde3",  # 边线
    "strategy": "#1f6feb",  # 策略净值主色
    "buy_hold": "#9aa3ad",  # 买入持有
    "up": "#16a34a",  # 绿（买点 / 分红贡献）
    "down": "#dc2626",  # 红（回撤 / 卖点）
    "accent2": "#5b8def",  # 蓝 2（价+现分）
    "reinvest": "#0ea5a4",  # 青（分红再投）
    "nav": "#8b95a3",  # 累计净值灰
}

_CN_FONTS = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]


def apply_theme() -> None:
    """设全局 rcParams（幂等）。白底、雅黑、去顶右边框、浅网格。"""
    plt.rcParams.update(
        {
            "font.sans-serif": _CN_FONTS + plt.rcParams["font.sans-serif"],
            "axes.unicode_minus": False,
            "figure.facecolor": THEME["bg"],
            "axes.facecolor": THEME["panel"],
            "axes.edgecolor": THEME["hair"],
            "axes.labelcolor": THEME["dim"],
            "axes.titlecolor": THEME["fg"],
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "xtick.color": THEME["dim"],
            "ytick.color": THEME["dim"],
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.grid": True,
            "grid.color": THEME["grid"],
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "legend.fontsize": 10,
        }
    )


apply_theme()  # import 即生效


# 顶部三行的固定 y（图坐标）：标题 → 副标题 → KPI（标签/值）。各行留足间距不重叠。
# 图函数的 axes top 应 ≤ _KPI_VALUE_Y - 0.05（≈0.78），给 KPI 值和图之间留白。
_TITLE_Y = 0.955
_SUBTITLE_Y = 0.910
_KPI_LABEL_Y = 0.858
_KPI_VALUE_Y = 0.828
_LEFT_X = 0.07  # 左边界，与 axes left 对齐


def title_block(fig: Figure, title: str, subtitle: str | None = None) -> None:
    """左上角标题（大）+ 副标题（小灰）。占顶部空间，留给 KPI / 图例。"""
    fig.text(_LEFT_X, _TITLE_Y, title, ha="left", va="center", fontsize=16,
             fontweight="bold", color=THEME["fg"])
    if subtitle:
        fig.text(_LEFT_X, _SUBTITLE_Y, subtitle, ha="left", va="center", fontsize=10.5,
                 color=THEME["dim"])


def kpi_strip(fig: Figure, items: Sequence[tuple[str, str, str]]) -> None:
    """副标题下方一行 KPI：``[(标签, 值, 颜色)]``，等间距横排。

    标签灰小字在上、值彩色大字在下，研报式。
    """
    if not items:
        return
    n = len(items)
    span = 0.93 - _LEFT_X  # 可用横向区间（左边界 → 0.93）
    step = span / n
    for i, (label, value, color) in enumerate(items):
        x = _LEFT_X + step * (i + 0.5)
        fig.text(x, _KPI_LABEL_Y, label, ha="center", va="center", fontsize=9,
                 color=THEME["faint"])
        fig.text(x, _KPI_VALUE_Y, value, ha="center", va="center", fontsize=13,
                 fontweight="bold", color=color)


def watermark(fig: Figure, text: str = "Vgrid 回测") -> None:
    """右下角浅灰水印。"""
    fig.text(0.985, 0.015, text, ha="right", va="bottom", fontsize=8.5,
             color=THEME["faint"], alpha=0.8)


def save_png(fig: Figure, path: Path | str, *, dpi: int = 160) -> Path:
    """保存 PNG（retina DPI，白底），关 figure。返回路径。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=dpi, bbox_inches="tight", facecolor=THEME["bg"])
    plt.close(fig)
    return p


def dec_pct(x: Decimal | float | None, digits: int = 2) -> str:
    """Decimal/float → '+12.34%'，None → '—'。"""
    if x is None:
        return "—"
    v = float(x) * 100
    return f"{v:+.{digits}f}%"


def dec_cash(x: Decimal | float | None, digits: int = 0) -> str:
    """Decimal/float → '¥12,345'，None → '—'。"""
    if x is None:
        return "—"
    return f"¥{float(x):,.{digits}f}"


def dec_price(x: Decimal | float | None, digits: int = 3) -> str:
    """价格 → '¥1.053'（round 到 digits 位），None → '—'。原始 Decimal 可能一长串，必须格式化。"""
    if x is None:
        return "—"
    return f"¥{float(x):.{digits}f}"


def xdates(ts: Sequence[datetime]) -> np.ndarray:
    """datetime 序列 → ndarray（matplotlib 画时间 x 轴用，stub 友好）。"""
    return np.asarray(ts, dtype=object)


def date_axis(ax: Axes) -> None:
    """给 x 轴套自适应日期格式：``ConciseDateFormatter`` 按跨度自动选粒度、去重相邻标签。"""
    locator = mdates.AutoDateLocator()  # type: ignore[no-untyped-call]
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))  # type: ignore[no-untyped-call]


def pct_formatter(values: Sequence[float]) -> FuncFormatter:
    """按数据跨度选百分比小数位（跨度小则多留一位），避免相邻刻度取整后重复。

    传入 y 值序列估跨度：跨度 < 8% 用 1 位小数，否则 0 位。
    """
    span = (max(values) - min(values)) if values else 0.0
    digits = 1 if span < 0.08 else 0  # noqa: PLR2004
    return FuncFormatter(lambda v, _=None: f"{v * 100:.{digits}f}%")
