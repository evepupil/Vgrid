"""回测 API 逻辑：``simulate`` + 结果转 JSON 安全 dict（纯逻辑，单测重点）。

和 ``state.py`` 一样是「跑引擎 + 转 dict」，但读的是缓存行情而非 SQLite tick。
曲线降采样到 500 点（前端渲染够用、精度够看）。回撤 / 买入持有对照序列（FR-7.3）在全量
曲线上算再按降采样索引对齐；期末阶梯（FR-7.4）复用跑完的引擎抽当前持仓/挂单。
"""

from __future__ import annotations

from vgrid.backtest import simulate_with_engine
from vgrid.backtest.result import BacktestResult, EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.models import Fill
from vgrid.strategy.ladder_view import build_ladder_view
from vgrid.web.curve import downsample
from vgrid.web.ladder_api import ladder_to_dict
from vgrid.web.series import buy_hold_series_from_bars, drawdown_series

_CURVE_POINTS = 500

# FR-7.5：回测报告恒定过拟合提示，前端照原样显示。
OVERFIT_NOTE = (
    "样本内最优，实盘未必——参数是在这段历史行情上调出来的，存在过拟合、滑点、流动性与"
    "参数漂移风险，务必用样本外区间与模拟盘二次验证。"
)


def run_backtest(
    bars: BarSeries, config: GridConfig, *, include_ladder: bool = True
) -> dict[str, object]:
    """对 ``bars`` 跑网格回测，返回 JSON 安全 dict。bars 为空由 ``simulate`` 抛错。"""
    result, engine = simulate_with_engine(config, bars)
    payload = _result_to_dict(result, config)
    if include_ladder and bars.bars:
        last_close = bars.bars[-1].close
        payload["end_ladder"] = ladder_to_dict(build_ladder_view(engine, last_close))
    else:
        payload["end_ladder"] = None
    return payload


def _result_to_dict(result: BacktestResult, config: GridConfig) -> dict[str, object]:
    m = result.metrics
    full = result.equity_curve
    curve, indices = downsample(full, _CURVE_POINTS)

    # 回撤 / 买入持有在全量曲线 / bar 上算，再按降采样索引对齐到 curve 的点（同 state.py 口径）
    dd_full = drawdown_series(full)
    bh_full = buy_hold_series_from_bars(result.bars, m.initial_cash, config)
    drawdown_curve = [{"ts": full[i].ts.isoformat(), "drawdown": str(dd_full[i])} for i in indices]
    buy_hold_curve = [{"ts": full[i].ts.isoformat(), "equity": str(bh_full[i])} for i in indices]

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
        "drawdown_curve": drawdown_curve,
        "buy_hold_curve": buy_hold_curve,
        "fills": [_fill(f) for f in result.fills],
        "n_bars": len(result.bars),
        "overfit_note": OVERFIT_NOTE,
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
