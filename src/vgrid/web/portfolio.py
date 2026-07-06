"""portfolio 组合层：聚合多个模拟盘实例 + 关注列表（纯逻辑 + 文件/DB I/O）。

实例 = ``~/.vgrid/paper/`` 下的 SQLite DB（每个 ``paper run --db`` 一个）。扫描目录
读各 DB replay 出状态聚合总资产。关注列表单独存 ``~/.vgrid/portfolio.sqlite``。

只读聚合（启停走 ``paper run`` CLI），网页看总资产 / 在跑实例 / 关注。``在跑`` 靠
最近 tick 时间判断（5 分钟内有 tick 视为活跃）。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from vgrid.store.db import connect
from vgrid.web.state import StateView, load_state

_RUNNING_THRESHOLD = timedelta(minutes=5)
_WATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    symbol    TEXT PRIMARY KEY,
    name      TEXT,
    added_at  TEXT NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class InstanceView:
    """一个模拟盘实例的聚合视图（前端列表 / 总资产用）。"""

    name: str
    db_path: str
    symbol: str
    status: str  # "running" / "idle"
    last_price: Decimal | None
    last_ts: datetime | None
    equity: Decimal
    realized_pnl: Decimal
    total_fee: Decimal
    open_lots: int
    n_fills: int


@dataclass(frozen=True, slots=True)
class WatchItem:
    """关注列表项。"""

    symbol: str
    name: str | None
    added_at: datetime


class PortfolioManager:
    """组合管理：扫 paper DB 聚合 + 关注列表 CRUD。"""

    def __init__(self, data_dir: Path, *, paper_dir: Path | None = None) -> None:
        self._data_dir = data_dir
        self._paper_dir = paper_dir or (data_dir / "paper")
        self._db_path = data_dir / "portfolio.sqlite"

    def list_instances(self) -> list[InstanceView]:
        """扫描 paper 目录，读各 DB replay 出实例视图。无 config 的 DB 跳过。"""
        views: list[InstanceView] = []
        if not self._paper_dir.exists():
            return views
        for db in sorted(self._paper_dir.glob("*.sqlite")):
            conn = connect(str(db))
            try:
                view = load_state(conn)
            finally:
                conn.close()
            if view is None:
                continue
            views.append(_to_instance(db.stem, str(db), view))
        return views

    def summary(self) -> dict[str, object]:
        """总资产 + 实例数 + 在跑数 + 累计已实现盈亏 / 手续费。"""
        insts = self.list_instances()
        return {
            "n_instances": len(insts),
            "n_running": sum(1 for i in insts if i.status == "running"),
            "total_equity": str(sum((i.equity for i in insts), Decimal(0))),
            "total_realized_pnl": str(sum((i.realized_pnl for i in insts), Decimal(0))),
            "total_fee": str(sum((i.total_fee for i in insts), Decimal(0))),
        }

    def list_watchlist(self) -> list[WatchItem]:
        conn = self._watch_conn()
        try:
            rows = conn.execute(
                "SELECT symbol, name, added_at FROM watchlist ORDER BY added_at"
            ).fetchall()
        finally:
            conn.close()
        return [
            WatchItem(
                symbol=r[0],
                name=r[1],
                added_at=datetime.fromisoformat(r[2]),
            )
            for r in rows
        ]

    def add_watch(self, symbol: str, name: str | None = None) -> None:
        """加入关注（同 symbol 覆盖）。"""
        conn = self._watch_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO watchlist(symbol, name, added_at) VALUES (?, ?, ?)",
                (symbol, name, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_watch(self, symbol: str) -> bool:
        """移除关注。不存在返回 False（幂等）。"""
        conn = self._watch_conn()
        try:
            cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def _watch_conn(self) -> sqlite3.Connection:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.executescript(_WATCH_SCHEMA)
        return conn


def _to_instance(name: str, db_path: str, view: StateView) -> InstanceView:
    snapshot = view.snapshot
    last_ts_raw = snapshot.get("last_ts")
    last_price_raw = snapshot.get("last_price")
    last_ts = last_ts_raw if isinstance(last_ts_raw, datetime) else None
    equity = view.equity_curve[-1].equity if view.equity_curve else Decimal(0)
    return InstanceView(
        name=name,
        db_path=db_path,
        symbol=view.symbol,
        status=_status(last_ts),
        last_price=last_price_raw if isinstance(last_price_raw, Decimal) else None,
        last_ts=last_ts,
        equity=equity,
        realized_pnl=_dec(snapshot.get("realized_pnl")),
        total_fee=_dec(snapshot.get("total_fee")),
        open_lots=_int(snapshot.get("open_lots")),
        n_fills=_int(snapshot.get("n_fills")),
    )


def _status(last_ts: datetime | None) -> str:
    if last_ts is None:
        return "idle"
    return "running" if datetime.now() - last_ts < _RUNNING_THRESHOLD else "idle"


def _dec(v: object) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(0)


def _int(v: object) -> int:
    return v if isinstance(v, int) else 0
