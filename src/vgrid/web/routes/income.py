"""红利 ETF 对比路由：``POST /api/income/compare``。

body 给区间 + 起始现金，外加 ``symbols``（给了就跳过关键词筛）或 ``keywords``（默认红利池）。
买入持有基线、四曲线口径都由 service 内部定，前端只传筛选条件。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vgrid.income.report import DEFAULT_SORT
from vgrid.income.service import IncomeCompareSpec
from vgrid.income.universe import DEFAULT_KEYWORDS
from vgrid.web.income_api import run_income_compare, run_income_enhance

router = APIRouter(prefix="/api/income", tags=["income"])


class IncomeCompareBody(BaseModel):
    start: date
    end: date
    keywords: list[str] | None = None  # None / 空列表 → 默认红利关键词池
    symbols: list[str] | None = None  # 给了就跳过关键词筛
    initial_cash: str = "100000"


@router.post("/compare")
def compare(body: IncomeCompareBody) -> dict[str, object]:
    """跑红利 ETF 对比，返排名 + 四曲线。"""
    keywords = tuple(body.keywords) if body.keywords else DEFAULT_KEYWORDS
    symbols = tuple(body.symbols) if body.symbols else ()
    try:
        initial = Decimal(body.initial_cash)
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail=f"起始现金非法：{body.initial_cash}") from exc
    spec = IncomeCompareSpec(
        start=body.start,
        end=body.end,
        keywords=keywords,
        symbols=symbols,
        initial_cash=initial,
        sort_keys=DEFAULT_SORT,
    )
    return run_income_compare(spec)


class IncomeEnhanceBody(BaseModel):
    symbol: str
    start: date
    end: date
    strategy: Literal["dca", "grid"]
    config: dict[str, object]  # dca=DcaConfig / grid=GridConfig 的 to_dict 格式


@router.post("/enhance")
def enhance(body: IncomeEnhanceBody) -> dict[str, object]:
    """单只红利 ETF：策略 + 分红再投增强，返策略 / 增强两条净值曲线 + 分红贡献。"""
    try:
        return run_income_enhance(
            symbol=body.symbol,
            start=body.start,
            end=body.end,
            strategy=body.strategy,
            config=body.config,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
