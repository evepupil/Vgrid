"""FastAPI 面板：读 SQLite 返回状态 JSON + HTML 面板。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from vgrid.backtest.result import EquityPoint
from vgrid.core.models import Fill
from vgrid.store.db import connect
from vgrid.web.state import FillMark, StateView, load_state

_TEMPLATE = Path(__file__).parent / "templates" / "index.html"


def create_app(default_db: str) -> FastAPI:
    """创建 FastAPI 应用；default_db 是 /api/state 的默认库路径。"""
    app = FastAPI(title="vgrid paper")

    @app.get("/api/state")
    def state(db: str | None = Query(default=None)) -> JSONResponse:
        path = db if db is not None else default_db
        conn = connect(path)
        try:
            view = load_state(conn)
        finally:
            conn.close()
        if view is None:
            return JSONResponse({"error": "no data"}, status_code=404)
        return JSONResponse(_to_json(view))

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _TEMPLATE.read_text(encoding="utf-8")

    return app


def _to_json(view: StateView) -> dict[str, object]:
    return {
        "symbol": view.symbol,
        "config": view.config,
        "snapshot": _jsonify(view.snapshot),
        "metrics": _jsonify(view.metrics),
        "fills": [_jsonify_fill(f) for f in view.fills],
        "equity_curve": [_jsonify_point(p) for p in view.equity_curve],
        "fill_marks": [_jsonify_mark(m) for m in view.fill_marks],
        "n_ticks": view.n_ticks,
    }


def _jsonify(obj: object) -> object:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonify(x) for x in obj]
    return obj


def _jsonify_fill(f: Fill) -> dict[str, object]:
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


def _jsonify_point(p: EquityPoint) -> dict[str, object]:
    return {"ts": p.ts.isoformat(), "equity": str(p.equity)}


def _jsonify_mark(m: FillMark) -> dict[str, object]:
    d: dict[str, object] = {
        "index": m.index,
        "side": m.side.value,
        "price": str(m.price),
        "shares": m.shares,
    }
    if m.realized_pnl is not None:
        d["realized_pnl"] = str(m.realized_pnl)
    return d
