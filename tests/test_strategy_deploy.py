"""策略增强 + 部署测试：草稿/已部署交叉引用、部署落库、冲突与缺失。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from vgrid.core.config import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.store.db import connect
from vgrid.store.repository import load_config
from vgrid.web.portfolio import PortfolioManager
from vgrid.web.strategy_deploy import (
    InstanceRef,
    deploy_strategy,
    enrich_strategies,
)
from vgrid.web.strategy_store import write_strategy


def _cfg(symbol: str = "159920") -> GridConfig:
    return GridConfig(
        symbol=symbol,
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=8,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def _write(strategies_dir: Path, name: str, symbol: str = "159920") -> None:
    write_strategy(strategies_dir, name, _cfg(symbol).to_dict())


def test_enrich_draft_when_no_instance(tmp_path: Path) -> None:
    _write(tmp_path, "恒生网格")
    rows = enrich_strategies(tmp_path, {})
    assert len(rows) == 1
    r = rows[0]
    assert r.status == "draft"
    assert r.instance_name is None
    assert r.sharpe is None
    assert r.symbol == "159920"


def test_enrich_deployed_links_instance(tmp_path: Path) -> None:
    _write(tmp_path, "恒生网格")
    instances = {"恒生网格": InstanceRef(name="恒生网格", status="running", sharpe="1.82")}
    r = enrich_strategies(tmp_path, instances)[0]
    assert r.status == "running"
    assert r.instance_name == "恒生网格"
    assert r.sharpe == "1.82"


def test_deploy_creates_instance_db(tmp_path: Path) -> None:
    strategies = tmp_path / "strategies"
    paper = tmp_path / "paper"
    _write(strategies, "恒生网格", symbol="510300")
    result = deploy_strategy(strategies, paper, "恒生网格", mode="sim")

    db = paper / "恒生网格.sqlite"
    assert db.exists()
    conn = connect(str(db))
    try:
        saved = load_config(conn)
    finally:
        conn.close()
    assert saved is not None and saved.symbol == "510300"
    assert result.symbol == "510300"
    assert result.mode == "sim"
    assert "paper run" in result.start_command
    assert "510300" in result.start_command


def test_deploy_twice_conflicts(tmp_path: Path) -> None:
    strategies = tmp_path / "strategies"
    paper = tmp_path / "paper"
    _write(strategies, "恒生网格")
    deploy_strategy(strategies, paper, "恒生网格")
    with pytest.raises(FileExistsError):
        deploy_strategy(strategies, paper, "恒生网格")


def test_deploy_missing_strategy_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        deploy_strategy(tmp_path / "strategies", tmp_path / "paper", "不存在")


def test_deployed_instance_shows_in_enrich(tmp_path: Path) -> None:
    # 部署后，该实例回放出的引用能把策略标成已部署
    strategies = tmp_path / "strategies"
    paper = tmp_path / "paper"
    _write(strategies, "恒生网格")
    deploy_strategy(strategies, paper, "恒生网格")
    # 部署只写 config、无 tick → 停歇；用组合层的口径模拟一个 idle 引用
    refs = {"恒生网格": InstanceRef(name="恒生网格", status="idle", sharpe="0")}
    r = enrich_strategies(strategies, refs)[0]
    assert r.status == "idle"
    assert r.instance_name == "恒生网格"


def test_deploy_lands_in_mode_dir(tmp_path: Path) -> None:
    """部署落 paper/{mode}/（routes 层拼路径口径）：该 mode 组合层能扫到、另一 mode 扫不到。"""
    strategies = tmp_path / "strategies"
    _write(strategies, "恒生网格")
    paper_dir = tmp_path / "paper" / "sim"  # 模拟 routes：data_dir/paper/{mode}
    result = deploy_strategy(strategies, paper_dir, "恒生网格", mode="sim")

    assert (paper_dir / "恒生网格.sqlite").exists()
    assert "paper/sim" in result.db_path.replace("\\", "/")
    sim_insts = PortfolioManager(tmp_path, mode="sim").list_instances()
    assert len(sim_insts) == 1 and sim_insts[0].name == "恒生网格"
    assert PortfolioManager(tmp_path, mode="live").list_instances() == []
