"""网格阶梯路由：``POST /api/ladder/preview``。

请求体给策略 config + 可选 ``price``（缺省用窗口中点）。返回该 config 在该价位
下的结构化阶梯，供前端画工程图。纯计算、不读库、不打网。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vgrid.core.config import GridConfig
from vgrid.web.ladder_api import preview_ladder

router = APIRouter(prefix="/api", tags=["ladder"])


class LadderPreviewBody(BaseModel):
    config: dict[str, object]
    price: str | None = None


@router.post("/ladder/preview")
def ladder_preview(body: LadderPreviewBody) -> dict[str, object]:
    try:
        config = GridConfig.from_dict(body.config)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"策略配置非法：{exc}") from exc
    price = _resolve_price(body.price, config)
    try:
        return preview_ladder(config, price)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=f"阶梯构建失败：{exc}") from exc


def _resolve_price(raw: str | None, config: GridConfig) -> Decimal:
    """price 缺省时取窗口中点。"""
    if raw is None:
        return (config.lower_price + config.upper_price) / 2
    try:
        price = Decimal(raw)
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail=f"价格非法：{raw}") from exc
    if not price.is_finite():  # 挡住 inf / -inf / NaN（review #34），否则进引擎行为未定义
        raise HTTPException(status_code=400, detail=f"价格必须为有限数：{raw}")
    return price
