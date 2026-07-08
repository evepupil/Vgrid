"""策略对比路由：``POST /api/compare``。

请求体给区间 + 周期 + 标的，外加网格 / 定投配置（至少一个）+ 可选起始现金（默认取网格
capital_cap，否则定投 cash_cap）。买入持有基线由后端自带，无需前端传。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.dca.config import DcaConfig
from vgrid.web.compare_api import run_compare

router = APIRouter(prefix="/api", tags=["compare"])


class CompareBody(BaseModel):
    symbol: str
    start: date
    end: date
    frame: str = "1d"
    initial_cash: str | None = None
    grid_config: dict[str, object] | None = None
    dca_config: dict[str, object] | None = None


@router.post("/compare")
def compare(body: CompareBody, request: Request) -> dict[str, object]:
    grid_cfg, dca_cfg = _parse_configs(body)
    if grid_cfg is None and dca_cfg is None:
        raise HTTPException(status_code=400, detail="至少要给网格或定投配置之一")
    try:
        frame = Frame(body.frame)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"周期非法：{body.frame}") from exc
    initial = _resolve_initial(body.initial_cash, grid_cfg, dca_cfg)

    bars = load_bars(
        body.symbol,
        body.start,
        body.end,
        frame,
        provider=getattr(request.app.state, "bar_provider", None),
        cache_dir=getattr(request.app.state, "cache_dir", None),
    )
    if not bars.bars:
        raise HTTPException(
            status_code=404, detail=f"{body.symbol} 在 {body.start} ~ {body.end} 无数据"
        )
    return run_compare(bars, initial_cash=initial, grid_config=grid_cfg, dca_config=dca_cfg)


def _parse_configs(body: CompareBody) -> tuple[GridConfig | None, DcaConfig | None]:
    try:
        grid_cfg = GridConfig.from_dict(body.grid_config) if body.grid_config is not None else None
        dca_cfg = DcaConfig.from_dict(body.dca_config) if body.dca_config is not None else None
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"配置非法：{exc}") from exc
    return grid_cfg, dca_cfg


def _resolve_initial(
    raw: str | None, grid_cfg: GridConfig | None, dca_cfg: DcaConfig | None
) -> Decimal:
    """起始现金：显式给就用，否则取网格 capital_cap，再否则定投 cash_cap。"""
    if raw is not None and raw != "":
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise HTTPException(status_code=400, detail=f"起始现金非法：{raw}") from exc
    if grid_cfg is not None:
        return grid_cfg.capital_cap
    if dca_cfg is not None:
        return dca_cfg.cash_cap
    raise HTTPException(status_code=400, detail="无法确定起始现金")  # 两个配置都无（已在上游拦）
