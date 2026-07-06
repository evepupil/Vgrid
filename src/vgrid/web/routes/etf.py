"""ETF 信息路由：查名称（输入代码自动拉取）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from vgrid.web.etf_info import get_etf_name

router = APIRouter(prefix="/api/etf", tags=["etf"])


@router.get("/{symbol}/info")
def info(symbol: str) -> dict[str, object]:
    name = get_etf_name(symbol)
    if name is None:
        raise HTTPException(status_code=404, detail=f"未找到 ETF：{symbol}")
    return {"symbol": symbol, "name": name}
