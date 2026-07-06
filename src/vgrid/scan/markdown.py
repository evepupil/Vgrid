"""扫描结果渲染成 Markdown（展示层，无单测）。

top-N 参数组合对比表，列「扫描字段 + 关键指标」，表头标「样本内最优」防过拟合误读。
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from vgrid.core.config import GridConfig
from vgrid.report._format import cash, dec, pct
from vgrid.scan.runner import ScanRow
from vgrid.scan.space import ScanSpec


def render_scan_report(rows: Sequence[ScanRow], metric: str, top_n: int, spec: ScanSpec) -> str:
    """渲染 top-N 扫描结果对比表。``rows`` 应已按 ``metric`` 排好序。"""
    shown = rows[:top_n]
    vary_keys = list(spec.vary)
    header = [*vary_keys, "夏普", "总收益", "年化", "最大回撤", "胜率", "末权益"]

    lines = [
        "# 网格参数扫描报告",
        "",
        f"按 `{metric}` 排序的前 {len(shown)} 组（共 {len(rows)} 组）。",
        "",
        "> ⚠️ 样本内最优，实盘未必——参数是在这段行情上调出来的，有过拟合风险。",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]

    for row in shown:
        cfg = row.config
        m = row.metrics
        params = [str(_cfg_field(cfg, k)) for k in vary_keys]
        cells = [
            *params,
            dec(m.sharpe),
            pct(m.total_return),
            pct(m.annualized_return),
            pct(m.max_drawdown),
            pct(m.win_rate),
            cash(m.final_equity),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)


def _cfg_field(cfg: GridConfig, key: str) -> object:
    """取 config 字段值用于展示；枚举显示 .value。"""
    value: object = getattr(cfg, key)
    return value.value if isinstance(value, Enum) else value
