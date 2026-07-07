"""portfolio 路由：总资产 / 在跑实例 / 关注列表。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from vgrid.data.mootdx_provider import symbol_exists
from vgrid.web.portfolio import InstanceView, PortfolioManager, WatchItem
from vgrid.web.watchlist_enrich import WatchlistEnricher, enriched_to_dict

router = APIRouter(tags=["portfolio"])


class WatchBody(BaseModel):
    symbol: str
    name: str | None = None


@router.get("/api/portfolio/summary")
def summary(
    request: Request, mode: Literal["live", "sim"] = Query(default="sim")
) -> dict[str, object]:
    return _mgr(request, mode).summary()


@router.get("/api/portfolio/runners")
def runners(
    request: Request, mode: Literal["live", "sim"] = Query(default="sim")
) -> list[dict[str, object]]:
    return [_instance_dict(i) for i in _mgr(request, mode).list_instances()]


@router.get("/api/watchlist")
def watchlist(request: Request) -> list[dict[str, object]]:
    return [_watch_dict(w) for w in _mgr(request).list_watchlist()]


@router.get("/api/watchlist/enriched")
def watchlist_enriched(request: Request) -> list[dict[str, object]]:
    """关注列表 + 实时行情 + 振幅 + 网格适配评分 + 近 N 日走势（FR-10.2~10.4）。"""
    items = _mgr(request).list_watchlist()
    enricher = WatchlistEnricher(
        request.app.state.quote_provider,
        bar_provider=getattr(request.app.state, "bar_provider", None),
        cache_dir=getattr(request.app.state, "cache_dir", None),
    )
    return [enriched_to_dict(e) for e in enricher.enrich(items)]


@router.post("/api/watchlist")
def add_watch(body: WatchBody, request: Request) -> dict[str, object]:
    """关注前先验证代码：mootdx 拉近期 K 线，无数据=404。

    用通达信协议（稳定不限 IP），不依赖东财现货源（海外易超时）。名称关注时不拉
    （避免 em 卡），列表展示时 ``enriched`` 现拉——拉不到该行显示代码本身。
    """
    if not symbol_exists(body.symbol):
        raise HTTPException(status_code=404, detail=f"未找到 ETF：{body.symbol}")
    _mgr(request).add_watch(body.symbol, body.name)
    return {"symbol": body.symbol, "name": body.name}


@router.delete("/api/watchlist/{symbol}")
def remove_watch(symbol: str, request: Request) -> dict[str, object]:
    if not _mgr(request).remove_watch(symbol):
        raise HTTPException(status_code=404, detail=f"未关注：{symbol}")
    return {"removed": symbol}


def _mgr(request: Request, mode: str = "sim") -> PortfolioManager:
    return PortfolioManager(Path(request.app.state.data_dir), mode=mode)


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
        "unrealized_pnl": str(i.unrealized_pnl),
        "committed": str(i.committed),
        "capital_cap": str(i.capital_cap),
        "position_shares": i.position_shares,
        "sharpe": str(i.sharpe),
        "max_drawdown": str(i.max_drawdown),
        "total_fee": str(i.total_fee),
        "open_lots": i.open_lots,
        "n_fills": i.n_fills,
        "equity_spark": [str(v) for v in i.equity_spark],
    }


def _watch_dict(w: WatchItem) -> dict[str, object]:
    return {
        "symbol": w.symbol,
        "name": w.name,
        "added_at": w.added_at.isoformat(),
    }
