"""回测路由：``POST /api/backtest``。

请求体给区间 + 周期 + 策略 config + 可选 ``symbol``（覆盖 config.symbol，方便同一套
策略参数测不同标的）。symbol 默认从 config 取（策略绑 ETF）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.web.backtest_api import run_backtest

router = APIRouter(prefix="/api", tags=["backtest"])


class BacktestBody(BaseModel):
    start: date
    end: date
    frame: str = "1d"
    config: dict[str, object]
    symbol: str | None = None


@router.post("/backtest")
def backtest(body: BacktestBody) -> dict[str, object]:
    try:
        config = GridConfig.from_dict(body.config)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"策略配置非法：{exc}") from exc
    if body.symbol is not None and body.symbol != config.symbol:
        config = replace(config, symbol=body.symbol)
    try:
        frame = Frame(body.frame)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"周期非法：{body.frame}") from exc
    bars = load_bars(config.symbol, body.start, body.end, frame)
    if not bars.bars:
        raise HTTPException(
            status_code=404,
            detail=f"{config.symbol} 在 {body.start} ~ {body.end} 无数据",
        )
    return run_backtest(bars, config)
