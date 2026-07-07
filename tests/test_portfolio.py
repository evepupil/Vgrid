"""portfolio 纯逻辑测试（tmp_path 临时目录，不碰网络）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from vgrid.core.config import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.store import connect, save_config, save_tick
from vgrid.web.portfolio import PortfolioManager


def _cfg(symbol: str = "159920") -> GridConfig:
    return GridConfig(
        symbol=symbol,
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def _seed(data_dir: Path, name: str, *, symbol: str = "159920", age: timedelta) -> None:
    paper_dir = data_dir / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(str(paper_dir / f"{name}.sqlite"))
    save_config(conn, _cfg(symbol))
    save_tick(conn, datetime.now() - age, Decimal("1.10"))
    conn.close()


def test_list_instances_empty(tmp_path: Path) -> None:
    assert PortfolioManager(tmp_path).list_instances() == []


def test_list_instances(tmp_path: Path) -> None:
    _seed(tmp_path, "a", symbol="159920", age=timedelta(minutes=1))
    _seed(tmp_path, "b", symbol="510300", age=timedelta(minutes=1))
    insts = PortfolioManager(tmp_path).list_instances()
    assert len(insts) == 2
    assert {i.symbol for i in insts} == {"159920", "510300"}
    assert all(i.status == "running" for i in insts)


def test_idle_status_when_old_tick(tmp_path: Path) -> None:
    _seed(tmp_path, "old", age=timedelta(days=1))
    insts = PortfolioManager(tmp_path).list_instances()
    assert insts[0].status == "idle"


def test_summary(tmp_path: Path) -> None:
    _seed(tmp_path, "a", age=timedelta(minutes=1))
    s = PortfolioManager(tmp_path).summary()
    assert s["n_instances"] == 1
    assert s["n_running"] == 1
    assert Decimal(str(s["total_equity"])) > 0


def test_summary_has_portfolio_aggregates(tmp_path: Path) -> None:
    _seed(tmp_path, "a", age=timedelta(minutes=1))
    s = PortfolioManager(tmp_path).summary()
    for key in ("total_unrealized_pnl", "total_committed", "total_cap"):
        assert key in s
    # 单实例，总额度 = 该实例资金上限 5 万
    assert Decimal(str(s["total_cap"])) == Decimal("50000")


def test_instance_view_enriched_fields(tmp_path: Path) -> None:
    _seed(tmp_path, "a", age=timedelta(minutes=1))
    inst = PortfolioManager(tmp_path).list_instances()[0]
    assert inst.capital_cap == Decimal("50000")
    assert isinstance(inst.unrealized_pnl, Decimal)
    assert isinstance(inst.position_shares, int)
    assert len(inst.equity_spark) >= 1  # 迷你净值有点


def test_watchlist_crud(tmp_path: Path) -> None:
    mgr = PortfolioManager(tmp_path)
    assert mgr.list_watchlist() == []
    mgr.add_watch("159920", "恒生")
    mgr.add_watch("510300")
    items = mgr.list_watchlist()
    assert len(items) == 2
    assert items[0].symbol == "159920"
    assert items[0].name == "恒生"
    assert mgr.remove_watch("159920") is True
    assert mgr.remove_watch("159920") is False  # 幂等
    assert len(mgr.list_watchlist()) == 1


def test_watchlist_overwrite_same_symbol(tmp_path: Path) -> None:
    mgr = PortfolioManager(tmp_path)
    mgr.add_watch("159920", "old")
    mgr.add_watch("159920", "new")
    items = mgr.list_watchlist()
    assert len(items) == 1
    assert items[0].name == "new"
