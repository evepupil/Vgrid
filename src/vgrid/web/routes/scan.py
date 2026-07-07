"""参数扫描路由：``POST /api/scan``。

请求体给区间 + 周期 + 扫描规格（``fixed`` / ``vary``）+ 排序指标 + top。symbol 从
``fixed.symbol`` 取。展开笛卡尔积逐组回测、按 metric 排序回 top-N。行情源 / 缓存目录
从 ``app.state`` 取，离线 / 测试可注入 stub。
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.scan import ScanSpec
from vgrid.scan.runner import Metric
from vgrid.web.scan_api import run_scan_api

router = APIRouter(prefix="/api", tags=["scan"])

_METRICS: frozenset[str] = frozenset(("sharpe", "total_return", "annualized_return", "calmar"))


class ScanBody(BaseModel):
    start: date
    end: date
    frame: str = "1d"
    fixed: dict[str, Any] = {}
    vary: dict[str, list[Any]] = {}
    metric: str = "sharpe"
    top: int = 10


@router.post("/scan")
def scan(body: ScanBody, request: Request) -> dict[str, object]:
    if body.metric not in _METRICS:
        raise HTTPException(status_code=400, detail=f"不支持的指标：{body.metric}")
    symbol = body.fixed.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        raise HTTPException(status_code=400, detail="fixed 必须含 symbol")
    try:
        spec = ScanSpec(fixed=body.fixed, vary=body.vary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"扫描规格非法：{exc}") from exc
    try:
        frame = Frame(body.frame)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"周期非法：{body.frame}") from exc
    bars = load_bars(
        symbol,
        body.start,
        body.end,
        frame,
        provider=getattr(request.app.state, "bar_provider", None),
        cache_dir=getattr(request.app.state, "cache_dir", None),
    )
    if not bars.bars:
        raise HTTPException(status_code=404, detail=f"{symbol} 在 {body.start} ~ {body.end} 无数据")
    try:
        return run_scan_api(spec, bars, metric=cast(Metric, body.metric), top=body.top)
    except ValueError as exc:  # 组合数超上限等
        raise HTTPException(status_code=400, detail=str(exc)) from exc
