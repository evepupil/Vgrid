"""state 路由：读模拟盘 SQLite replay 出状态 JSON（旧看盘面板用）。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from vgrid.analysis.stress import StressReport
from vgrid.backtest.result import EquityPoint
from vgrid.core.models import Fill
from vgrid.store.db import connect
from vgrid.web.jsonify import jsonify
from vgrid.web.ladder_api import ladder_to_dict
from vgrid.web.state import FillMark, StateView, load_state

router = APIRouter(tags=["state"])


@router.get("/api/state")
def state(request: Request, db: str | None = Query(default=None)) -> JSONResponse:
    """读库 replay 出面板状态。无 config 返 404。

    GET 不建库、校验 ``db`` 路径落在 ``data_dir`` 内（review #24）——否则一个带
    ``db=../../foo.sqlite`` 的 GET 会在磁盘上凭空建出空 sqlite 库，还能路径遍历。
    """
    data_dir = Path(request.app.state.data_dir).resolve()
    if db is not None:
        candidate = Path(db)
        path = (candidate if candidate.is_absolute() else data_dir / candidate).resolve()
        if not path.is_relative_to(data_dir):
            return JSONResponse({"error": "db 路径越界"}, status_code=400)
    else:
        path = Path(request.app.state.default_db)
    if not path.exists():
        return JSONResponse({"error": "库不存在"}, status_code=404)
    conn = connect(str(path))
    try:
        view = load_state(conn)
    finally:
        conn.close()
    if view is None:
        return JSONResponse({"error": "no data"}, status_code=404)
    return JSONResponse(_state_to_dict(view))


def _state_to_dict(view: StateView) -> dict[str, object]:
    return {
        "symbol": view.symbol,
        "config": view.config,
        "snapshot": jsonify(view.snapshot),
        "metrics": jsonify(view.metrics),
        "fills": [_fill_to_dict(f) for f in view.fills],
        "equity_curve": [_point_to_dict(p) for p in view.equity_curve],
        "drawdown_curve": [
            {"ts": ts.isoformat(), "drawdown": str(v)} for ts, v in view.drawdown_curve
        ],
        "buy_hold_curve": [
            {"ts": ts.isoformat(), "equity": str(v)} for ts, v in view.buy_hold_curve
        ],
        "fill_marks": [_mark_to_dict(m) for m in view.fill_marks],
        "n_ticks": view.n_ticks,
        "ladder": ladder_to_dict(view.ladder) if view.ladder is not None else None,
        "risk": _risk_to_dict(view.risk) if view.risk is not None else None,
    }


def _risk_to_dict(r: StressReport) -> dict[str, object]:
    return {
        "occupancy": {
            "committed": str(r.occupancy.committed),
            "capital_cap": str(r.occupancy.capital_cap),
            "ratio_pct": str(r.occupancy.ratio_pct),
            "buffer_pct": str(r.occupancy.buffer_pct),
        },
        "scenarios": [
            {
                "drop_pct": str(s.drop_pct),
                "scenario_price": str(s.scenario_price),
                "position_loss": str(s.position_loss),
                "projected_unrealized": str(s.projected_unrealized),
            }
            for s in r.scenarios
        ],
        "amplification": {
            "lower_price": str(r.amplification.lower_price),
            "down_spacing_factor": str(r.amplification.down_spacing_factor),
            "down_amount_factor": str(r.amplification.down_amount_factor),
            "enabled": r.amplification.enabled,
            "note": r.amplification.note,
        },
        "max_occupancy": str(r.max_occupancy),
    }


def _fill_to_dict(f: Fill) -> dict[str, object]:
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


def _point_to_dict(p: EquityPoint) -> dict[str, object]:
    return {"ts": p.ts.isoformat(), "equity": str(p.equity)}


def _mark_to_dict(m: FillMark) -> dict[str, object]:
    d: dict[str, object] = {
        "index": m.index,
        "side": m.side.value,
        "price": str(m.price),
        "shares": m.shares,
    }
    if m.realized_pnl is not None:
        d["realized_pnl"] = str(m.realized_pnl)
    return d
