"""定投回测 API 逻辑：``run_dca`` + 结果转 JSON 安全 dict。

和 ``backtest_api`` 同结构：跑引擎 → 曲线降采样到 500 点 → 回撤 / 买入持有对照序列在全量
曲线上算再按降采样索引对齐。指标带 XIRR（无解为 null）和「累计投入 / 投入回报」这些定投
特有项。
"""

from __future__ import annotations

from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.dca.config import DcaConfig
from vgrid.dca.engine import run_dca
from vgrid.dca.result import DcaResult, DcaTrade
from vgrid.web.curve import downsample
from vgrid.web.series import buy_hold_series_from_bars, drawdown_series

_CURVE_POINTS = 500


def run_dca_backtest(bars: BarSeries, config: DcaConfig) -> dict[str, object]:
    """对 ``bars`` 跑定投回测，返回 JSON 安全 dict。bars 为空由 ``run_dca`` 抛错。"""
    return _result_to_dict(run_dca(config, bars), config)


def _result_to_dict(result: DcaResult, config: DcaConfig) -> dict[str, object]:
    m = result.metrics
    full = result.equity_curve
    curve, indices = downsample(full, _CURVE_POINTS)

    dd_full = drawdown_series(full)
    bh_full = buy_hold_series_from_bars(
        result.bars, m.initial_cash, fee=config.fee, lot_size=config.lot_size
    )
    drawdown_curve = [{"ts": full[i].ts.isoformat(), "drawdown": str(dd_full[i])} for i in indices]
    buy_hold_curve = [{"ts": full[i].ts.isoformat(), "equity": str(bh_full[i])} for i in indices]

    return {
        "metrics": {
            "initial_cash": str(m.initial_cash),
            "invested_amount": str(m.invested_amount),
            "final_cash": str(m.final_cash),
            "final_market_value": str(m.final_market_value),
            "final_equity": str(m.final_equity),
            "profit": str(m.profit),
            "profit_on_invested": str(m.profit_on_invested),
            "profit_rate_on_invested": str(m.profit_rate_on_invested),
            "xirr": str(m.xirr) if m.xirr is not None else None,
            "max_drawdown": str(m.max_drawdown),
            "total_fee": str(m.total_fee),
            "n_buys": m.n_buys,
            "skipped_count": m.skipped_count,
            "buy_hold_return": str(m.buy_hold_return),
        },
        "equity_curve": [_point(p) for p in curve],
        "drawdown_curve": drawdown_curve,
        "buy_hold_curve": buy_hold_curve,
        "trades": [_trade(t) for t in result.trades],
        "skipped": [{"ts": s.ts.isoformat(), "reason": s.reason} for s in result.skipped],
        "n_bars": len(result.bars),
    }


def _point(p: EquityPoint) -> dict[str, object]:
    return {"ts": p.ts.isoformat(), "equity": str(p.equity)}


def _trade(t: DcaTrade) -> dict[str, object]:
    return {
        "ts": t.ts.isoformat(),
        "price": str(t.price),
        "shares": t.shares,
        "notional": str(t.notional),
        "fee": str(t.fee),
        "multiplier": str(t.multiplier),
    }
