"""portfolio 路由：总资产 / 在跑实例 / 关注列表。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vgrid.web.portfolio import InstanceView, PortfolioManager, WatchItem

router = APIRouter(tags=["portfolio"])


class WatchBody(BaseModel):
    symbol: str
    name: str | None = None


@router.get("/api/portfolio/summary")
def summary(request: Request) -> dict[str, object]:
    return _mgr(request).summary()


@router.get("/api/portfolio/runners")
def runners(request: Request) -> list[dict[str, object]]:
    return [_instance_dict(i) for i in _mgr(request).list_instances()]


@router.get("/api/watchlist")
def watchlist(request: Request) -> list[dict[str, object]]:
    return [_watch_dict(w) for w in _mgr(request).list_watchlist()]


@router.post("/api/watchlist")
def add_watch(body: WatchBody, request: Request) -> dict[str, object]:
    _mgr(request).add_watch(body.symbol, body.name)
    return {"symbol": body.symbol, "name": body.name}


@router.delete("/api/watchlist/{symbol}")
def remove_watch(symbol: str, request: Request) -> dict[str, object]:
    if not _mgr(request).remove_watch(symbol):
        raise HTTPException(status_code=404, detail=f"未关注：{symbol}")
    return {"removed": symbol}


def _mgr(request: Request) -> PortfolioManager:
    return PortfolioManager(Path(request.app.state.data_dir))


def _instance_dict(i: InstanceView) -> dict[str, object]:
    return {
        "name": i.name,
        "db_path": i.db_path,
        "symbol": i.symbol,
        "status": i.status,
        "last_price": str(i.last_price) if i.last_price is not None else None,
        "last_ts": i.last_ts.isoformat() if i.last_ts is not None else None,
        "equity": str(i.equity),
        "realized_pnl": str(i.realized_pnl),
        "total_fee": str(i.total_fee),
        "open_lots": i.open_lots,
        "n_fills": i.n_fills,
    }


def _watch_dict(w: WatchItem) -> dict[str, object]:
    return {
        "symbol": w.symbol,
        "name": w.name,
        "added_at": w.added_at.isoformat(),
    }
