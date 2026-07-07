"""报价路由：``GET /api/quotes?symbols=a,b,c``。

多标的实时现价 + 昨收 + 涨跌，供顶部 ticker / 关注列表 / 标的头共用。行情源任何失败
都降级为空列表（带 error 说明），绝不让看盘页崩——实时性让位于稳定性。
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from vgrid.web.quotes import QuoteProvider, quote_to_dict

router = APIRouter(prefix="/api", tags=["quotes"])


@router.get("/quotes")
def quotes(request: Request, symbols: str = Query(default="")) -> dict[str, object]:
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    if not syms:
        return {"quotes": [], "error": None}
    provider: QuoteProvider = request.app.state.quote_provider
    try:
        result = provider.fetch_many(syms)
    except Exception as exc:  # 行情源任何失败都降级为空，不能让看盘页崩
        return {"quotes": [], "error": f"行情源不可用：{exc}"}
    return {"quotes": [quote_to_dict(q) for q in result], "error": None}
