"""策略库路由：``strategies/`` 目录 CRUD。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vgrid.web.strategy_store import (
    StrategySummary,
    delete_strategy,
    list_strategies,
    read_strategy,
    write_strategy,
)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class StrategyBody(BaseModel):
    """创建策略的请求体：name + 完整 config dict。"""

    name: str
    config: dict[str, object]


@router.get("")
def list_all(request: Request) -> list[dict[str, object]]:
    return [_summary_to_dict(s) for s in list_strategies(_dir(request))]


@router.get("/{name}")
def get_one(name: str, request: Request) -> dict[str, object]:
    try:
        return read_strategy(_dir(request), name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"策略不存在：{name}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("")
def create(body: StrategyBody, request: Request) -> dict[str, object]:
    try:
        write_strategy(_dir(request), body.name, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return read_strategy(_dir(request), body.name)


@router.put("/{name}")
def update(name: str, body: dict[str, object], request: Request) -> dict[str, object]:
    try:
        write_strategy(_dir(request), name, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return read_strategy(_dir(request), name)


@router.delete("/{name}")
def remove(name: str, request: Request) -> dict[str, object]:
    try:
        deleted = delete_strategy(_dir(request), name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"策略不存在：{name}")
    return {"deleted": name}


def _dir(request: Request) -> Path:
    return Path(request.app.state.strategies_dir)


def _summary_to_dict(s: StrategySummary) -> dict[str, object]:
    return {
        "name": s.name,
        "symbol": s.symbol,
        "spacing_mode": s.spacing_mode,
        "base_build_mode": s.base_build_mode,
        "grid_count": s.grid_count,
        "lower_price": s.lower_price,
        "upper_price": s.upper_price,
    }
