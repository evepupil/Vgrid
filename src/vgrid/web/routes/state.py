"""state 路由：读模拟盘 SQLite replay 出状态 JSON（旧看盘面板用）。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from vgrid.backtest.result import EquityPoint
from vgrid.core.models import Fill
from vgrid.store.db import connect
from vgrid.web.jsonify import jsonify
from vgrid.web.ladder_api import ladder_to_dict
from vgrid.web.state import FillMark, StateView, load_state

router = APIRouter(tags=["state"])


@router.get("/api/state")
def state(request: Request, db: str | None = Query(default=None)) -> JSONResponse:
    """读库 replay 出面板状态。无 config 返 404。"""
    path = db if db is not None else request.app.state.default_db
    conn = connect(path)
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
