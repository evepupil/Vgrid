"""图 F：参数扫描热力图。

把两参数网格扫描的结果画成 ``x × y`` 热力图（颜色 = 指标值，默认夏普），最优点标星。
要求 ``ScanSpec.vary`` 恰好两个维度（笛卡尔积铺成二维表）；其它维度扫描不适合单张热力图。
"""

from __future__ import annotations

from enum import Enum

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

from vgrid.charts._style import THEME, kpi_strip, title_block, watermark
from vgrid.scan.runner import Metric, ScanRow, metric_value
from vgrid.scan.space import ScanSpec

_N_DIMS = 2  # 热力图恰好两个扫描维度
_PCT_METRICS = ("total_return", "annualized_return", "calmar")


def _field(cfg: object, key: str) -> object:
    value = getattr(cfg, key)
    return value.value if isinstance(value, Enum) else value


def _pct_fmt(metric: Metric) -> PercentFormatter | None:
    return PercentFormatter(1.0) if metric in _PCT_METRICS else None


def render_scan_heatmap(
    rows: list[ScanRow], *, metric: Metric, spec: ScanSpec,
) -> Figure:
    """两参数 × 指标 热力图，最优点标星。``spec.vary`` 必须恰好两个维度。"""
    keys = list(spec.vary)
    if len(keys) != _N_DIMS:
        raise ValueError(f"热力图需恰好 {_N_DIMS} 个扫描维度，当前 {len(keys)}：{keys}")
    x_key, y_key = keys
    x_vals = list(spec.vary[x_key])
    y_vals = list(spec.vary[y_key])
    if not rows or not x_vals or not y_vals:
        raise ValueError("扫描结果或维度为空，无法画热力图")

    # 行 → 二维矩阵：matrix[j, i] = 该 (x, y) 组合的指标值，缺组合留 NaN。
    matrix = np.full((len(y_vals), len(x_vals)), np.nan)
    for row in rows:
        xv, yv = _field(row.config, x_key), _field(row.config, y_key)
        if xv in x_vals and yv in y_vals:
            matrix[y_vals.index(yv), x_vals.index(xv)] = float(metric_value(row, metric))

    best_ji = np.nanargmax(matrix) if not np.all(np.isnan(matrix)) else None

    fig = plt.figure(figsize=(8.5, 6))
    ax = fig.add_axes((0.16, 0.16, 0.66, 0.60))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto", origin="lower")

    ax.set_xticks(range(len(x_vals)))
    ax.set_xticklabels([str(v) for v in x_vals])
    ax.set_yticks(range(len(y_vals)))
    ax.set_yticklabels([str(v) for v in y_vals])
    ax.set_xlabel(x_key)
    ax.set_ylabel(y_key)
    ax.grid(visible=False)

    # 每格标数值（NaN 留空）。
    pct = _pct_fmt(metric)
    for j in range(len(y_vals)):
        for i in range(len(x_vals)):
            v = matrix[j, i]
            if np.isnan(v):
                continue
            txt = f"{v * 100:.1f}%" if pct else f"{v:.2f}"
            ax.text(i, j, txt, ha="center", va="center", fontsize=8.5,
                    color=THEME["fg"] if v < np.nanmax(matrix) * 0.7 else "#ffffff")
    if best_ji is not None:
        bj, bi = divmod(best_ji, len(x_vals))
        ax.scatter([bi], [bj], marker="*", s=240, color=THEME["down"],
                   edgecolors="white", linewidths=0.8, zorder=5)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    if pct:
        cbar.ax.yaxis.set_major_formatter(pct)

    metric_label = {"sharpe": "夏普", "total_return": "总收益",
                    "annualized_return": "年化", "calmar": "Calmar"}[metric]
    title_block(fig, "参数扫描热力图", f"颜色 = {metric_label} · {len(rows)} 组")
    best_txt = "—"
    if best_ji is not None and not np.isnan(matrix.flatten()[best_ji]):
        bv = float(matrix.flatten()[best_ji])
        best_txt = f"{bv * 100:.1f}%" if pct else f"{bv:.2f}"
    kpi_strip(fig, [
        ("X 轴", x_key, THEME["dim"]),
        ("Y 轴", y_key, THEME["dim"]),
        (f"最优 {metric_label}", best_txt, THEME["up"]),
        ("组合数", str(len(rows)), THEME["dim"]),
    ])
    watermark(fig)
    return fig
