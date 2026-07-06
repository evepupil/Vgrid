"""回测 API 逻辑：``simulate`` + 结果转 JSON 安全 dict（纯逻辑，单测重点）。

和 ``state.py`` 一样是「跑引擎 + 转 dict」，但读的是缓存行情而非 SQLite tick。
曲线降采样到 500 点（前端渲染够用、精度够看）。
"""

from __future__ import annotations

from vgrid.backtest import simulate
from vgrid.backtest.result import BacktestResult, EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.models import Fill
from vgrid.web.curve import downsample

_CURVE_POINTS = 500


def run_backtest(bars: BarSeries, config: GridConfig) -> dict[str, object]:
    """对 ``bars`` 跑网格回测，返回 JSON 安全 dict。bars 为空由 ``simulate`` 抛错。"""
    result = simulate(config, bars)
    return _result_to_dict(result)


def _result_to_dict(result: BacktestResult) -> dict[str, object]:
    m = result.metrics
    curve, _ = downsample(result.equity_curve, _CURVE_POINTS)
    return {
        "metrics": {
            "initial_cash": str(m.initial_cash),
            "final_equity": str(m.final_equity),
            "total_return": str(m.total_return),
            "annualized_return": str(m.annualized_return),
            "max_drawdown": str(m.max_drawdown),
            "sharpe": str(m.sharpe),
            "win_rate": str(m.win_rate),
            "profit_loss_ratio": str(m.profit_loss_ratio),
            "n_buys": m.n_buys,
            "n_sells": m.n_sells,
            "total_fee": str(m.total_fee),
            "buy_hold_return": str(m.buy_hold_return),
        },
        "equity_curve": [_point(p) for p in curve],
        "fills": [_fill(f) for f in result.fills],
        "n_bars": len(result.bars),
    }


def _point(p: EquityPoint) -> dict[str, object]:
    return {"ts": p.ts.isoformat(), "equity": str(p.equity)}


def _fill(f: Fill) -> dict[str, object]:
    d: dict[str, object] = {
        "ts": f.ts.isoformat() if f.ts is not None else "",
        "side": f.side.value,
        "price": str(f.price),
        "shares": f.shares,
        "fee": str(f.fee),
    }
    if f.realized_pnl is not None:
        d["realized_pnl"] = str(f.realized_pnl)
    return d
