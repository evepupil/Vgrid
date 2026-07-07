"""参数扫描 API 逻辑：spec → 跑扫描 → top-N JSON 安全 dict（纯逻辑，单测重点）。

复用 ``scan`` 模块（``ScanSpec.expand`` 笛卡尔积 + ``run_scan`` + ``rank``）。前端给
``fixed`` / ``vary``，这里展开、逐组回测、按 metric 排序、切 top-N，回每组扫描字段值 +
关键指标。同样带样本内最优提示（FR-8 复用 FR-7.5 文案）。
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig
from vgrid.scan import ScanSpec, rank, run_scan
from vgrid.scan.runner import Metric, ScanRow
from vgrid.web.backtest_api import OVERFIT_NOTE


def run_scan_api(
    spec: ScanSpec,
    bars: BarSeries,
    *,
    metric: Metric,
    top: int,
    initial_cash: Decimal | None = None,
) -> dict[str, object]:
    """展开 spec、逐组回测、按 ``metric`` 排序、切前 ``top`` 组，返回 JSON 安全 dict。"""
    configs = spec.expand()
    rows = run_scan(configs, bars, initial_cash=initial_cash)
    ranked = rank(rows, metric)
    shown = ranked[: max(0, top)]
    vary_keys = list(spec.vary)
    return {
        "metric": metric,
        "total": len(rows),  # 扫了多少组
        "shown": len(shown),
        "vary_keys": vary_keys,
        "rows": [_row_to_dict(r, vary_keys) for r in shown],
        "overfit_note": OVERFIT_NOTE,
    }


def _row_to_dict(row: ScanRow, vary_keys: list[str]) -> dict[str, object]:
    m = row.metrics
    return {
        "params": {k: _cfg_field(row.config, k) for k in vary_keys},
        "metrics": {
            "sharpe": str(m.sharpe),
            "total_return": str(m.total_return),
            "annualized_return": str(m.annualized_return),
            "max_drawdown": str(m.max_drawdown),
            "win_rate": str(m.win_rate),
            "final_equity": str(m.final_equity),
            "n_buys": m.n_buys,
            "n_sells": m.n_sells,
        },
    }


def _cfg_field(config: GridConfig, key: str) -> object:
    """取 config 字段值用于展示：枚举 → .value，Decimal / int 转 str/int（JSON 安全）。"""
    value: object = getattr(config, key)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    return value
