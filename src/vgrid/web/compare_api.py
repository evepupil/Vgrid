"""策略对比 API 逻辑：``compare_strategies`` + 结果转 JSON 安全 dict。

每个策略带一条降采样净值曲线（供前端叠加），加对比行（末权益 / 收益率 / 年化 / 回撤 /
手续费 / 定投的投入 + XIRR）。曲线降采样到 500 点；三条曲线同长同时间轴，索引对齐后可直接叠加。
"""

from __future__ import annotations

from decimal import Decimal

from vgrid.backtest.compare import StrategyRow, compare_strategies
from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig
from vgrid.dca.config import DcaConfig
from vgrid.web.curve import downsample

_CURVE_POINTS = 500


def run_compare(
    bars: BarSeries,
    *,
    initial_cash: Decimal,
    grid_config: GridConfig | None = None,
    dca_config: DcaConfig | None = None,
) -> dict[str, object]:
    """跑三方对比，返回 JSON 安全 dict（行 + 各自净值曲线）。"""
    comparison = compare_strategies(
        bars, initial_cash=initial_cash, grid_config=grid_config, dca_config=dca_config
    )
    return {
        "initial_cash": str(comparison.initial_cash),
        "first_day": comparison.bars[0].ts.date().isoformat(),
        "last_day": comparison.bars[-1].ts.date().isoformat(),
        "n_bars": len(comparison.bars),
        "rows": [_row_to_dict(r) for r in comparison.rows],
    }


def _row_to_dict(r: StrategyRow) -> dict[str, object]:
    curve, _ = downsample(r.curve, _CURVE_POINTS)
    return {
        "name": r.name,
        "final_equity": str(r.final_equity),
        "profit": str(r.profit),
        "total_return": str(r.total_return),
        "annualized_return": str(r.annualized_return),
        "max_drawdown": str(r.max_drawdown),
        "total_fee": str(r.total_fee),
        "n_trades": r.n_trades,
        "invested": str(r.invested) if r.invested is not None else None,
        "xirr": str(r.xirr) if r.xirr is not None else None,
        "curve": [_point(p) for p in curve],
    }


def _point(p: EquityPoint) -> dict[str, object]:
    return {"ts": p.ts.isoformat(), "equity": str(p.equity)}
