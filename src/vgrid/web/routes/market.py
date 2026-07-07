"""市场时段路由：``GET /api/market/status?market=沪深``（FR-11.2）。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from vgrid.web.market import market_status

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status")
def status(market: str = Query(default="沪深")) -> dict[str, object]:
    s = market_status(datetime.now(), market)
    return {
        "market": s.market,
        "status": s.status,
        "label": s.label,
        "now": s.now.isoformat(),
        "note": s.note,
    }
