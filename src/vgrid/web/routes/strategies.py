"""策略库路由：``strategies/`` 目录 CRUD。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from vgrid.web.portfolio import PortfolioManager
from vgrid.web.strategy_deploy import (
    DeployResult,
    EnrichedStrategy,
    InstanceRef,
    deploy_strategy,
    deployed_modes,
    enrich_strategies,
)
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


class DeployBody(BaseModel):
    """部署请求体：目标 mode（当前 live/sim 都落模拟盘库，实盘执行是后续 slice）。"""

    mode: Literal["live", "sim"] = "sim"


@router.get("")
def list_all(request: Request) -> list[dict[str, object]]:
    return [_summary_to_dict(s) for s in list_strategies(_dir(request))]


@router.get("/enriched")
def list_enriched(
    request: Request, mode: Literal["live", "sim"] = Query(default="sim")
) -> list[dict[str, object]]:
    """策略 + 部署状态 + 关联实例夏普（FR-9.2）。

    实例按 mode 隔离，只交叉引用当前 mode 的实例（FR-1.1）。
    """
    instances = _instance_refs(request, mode)
    return [_enriched_to_dict(e) for e in enrich_strategies(_dir(request), instances)]


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
    except (ValueError, KeyError) as exc:
        # GridConfig.from_dict 缺必填字段抛 KeyError（review #26），统一回 400 而非 500
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return read_strategy(_dir(request), body.name)


@router.put("/{name}")
def update(name: str, body: dict[str, object], request: Request) -> dict[str, object]:
    # 已部署成实例的策略不让改配置：DB / 内存引擎里冻着旧 config，改文件会三者脱节（review #25）。
    deployed = deployed_modes(Path(request.app.state.data_dir), name)
    if deployed:
        raise HTTPException(
            status_code=409,
            detail=f"策略 {name} 已部署为实例（{'/'.join(deployed)}），先停并删除实例再改配置",
        )
    try:
        write_strategy(_dir(request), name, body)
    except (ValueError, KeyError) as exc:
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


@router.post("/{name}/deploy")
def deploy(name: str, body: DeployBody, request: Request) -> dict[str, object]:
    """把策略部署为运行实例（FR-9.3）。按 mode 落对应目录（FR-1.1）。已部署返回 409。"""
    paper_dir = Path(request.app.state.data_dir) / "paper" / body.mode
    try:
        result = deploy_strategy(_dir(request), paper_dir, name, mode=body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"策略不存在：{name}") from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _deploy_to_dict(result)


def _dir(request: Request) -> Path:
    return Path(request.app.state.strategies_dir)


def _instance_refs(request: Request, mode: str = "sim") -> dict[str, InstanceRef]:
    mgr = PortfolioManager(Path(request.app.state.data_dir), mode=mode)
    return {
        i.name: InstanceRef(name=i.name, status=i.status, sharpe=str(i.sharpe))
        for i in mgr.list_instances()
    }


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


def _enriched_to_dict(e: EnrichedStrategy) -> dict[str, object]:
    return {
        "name": e.name,
        "symbol": e.symbol,
        "spacing_mode": e.spacing_mode,
        "base_build_mode": e.base_build_mode,
        "grid_count": e.grid_count,
        "lower_price": e.lower_price,
        "upper_price": e.upper_price,
        "status": e.status,
        "instance_name": e.instance_name,
        "sharpe": e.sharpe,
    }


def _deploy_to_dict(r: DeployResult) -> dict[str, object]:
    return {
        "instance_name": r.instance_name,
        "db_path": r.db_path,
        "symbol": r.symbol,
        "mode": r.mode,
        "start_command": r.start_command,
    }
