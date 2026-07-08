"""存取 tick / fill / config。纯 I/O，类型转换集中在此。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal

from vgrid.core.config import GridConfig
from vgrid.core.enums import Side
from vgrid.core.models import Fill


def save_config(conn: sqlite3.Connection, config: GridConfig) -> None:
    """单行 upsert（id 固定为 1）。"""
    conn.execute(
        "INSERT INTO config(id, json) VALUES (1, ?)"
        " ON CONFLICT(id) DO UPDATE SET json = excluded.json",
        (json.dumps(config.to_dict(), ensure_ascii=False),),
    )
    conn.commit()


def load_config(conn: sqlite3.Connection) -> GridConfig | None:
    row = conn.execute("SELECT json FROM config WHERE id = 1").fetchone()
    if row is None:
        return None
    return GridConfig.from_dict(json.loads(row[0]))


def save_tick(conn: sqlite3.Connection, ts: datetime, price: Decimal) -> None:
    """追加一条 tick（seq 自增主键，同 ts 不再覆盖——见 db.py 的说明）。"""
    conn.execute(
        "INSERT INTO tick(ts, price) VALUES (?, ?)",
        (ts.isoformat(), str(price)),
    )
    conn.commit()


def save_tick_with_fills(
    conn: sqlite3.Connection, ts: datetime, price: Decimal, fills: list[Fill]
) -> None:
    """一个 tick + 它触发的全部 fills 包进单事务、末尾一次 commit（review #21）。

    半写会让 fills 表与引擎状态发散：tick 进去了但 fills 只进了一部分，重启 replay 用
    tick 重建引擎（状态对），但 fills 表缺行 → ``snapshot.n_fills`` 与 ``sum(realized_pnl)``
    和引擎内存对不上。单事务保证要么全进、要么全不进。
    """
    with conn:  # 退出时 commit；中途异常自动 rollback
        conn.execute(
            "INSERT INTO tick(ts, price) VALUES (?, ?)",
            (ts.isoformat(), str(price)),
        )
        for f in fills:
            _insert_fill(conn, f)


def load_ticks(conn: sqlite3.Connection) -> list[tuple[datetime, Decimal]]:
    """按 seq（到达顺序）升序返回全部 tick——replay 必须按原跑顺序回放（review #22）。"""
    rows = conn.execute("SELECT ts, price FROM tick ORDER BY seq").fetchall()
    return [(datetime.fromisoformat(r[0]), Decimal(r[1])) for r in rows]


def save_fill(conn: sqlite3.Connection, fill: Fill) -> None:
    """追加一笔成交（UNIQUE 自然键防重复——review #35）。"""
    _insert_fill(conn, fill)
    conn.commit()


def _insert_fill(conn: sqlite3.Connection, fill: Fill) -> None:
    conn.execute(
        "INSERT INTO fill(ts, side, price, shares, fee, level_index, realized_pnl)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            fill.ts.isoformat() if fill.ts is not None else "",
            fill.side.value,
            str(fill.price),
            fill.shares,
            str(fill.fee),
            fill.level_index,
            str(fill.realized_pnl) if fill.realized_pnl is not None else None,
        ),
    )


def load_fills(conn: sqlite3.Connection) -> list[Fill]:
    """按 seq（写入顺序）升序返回全部成交。"""
    rows = conn.execute(
        "SELECT ts, side, price, shares, fee, level_index, realized_pnl FROM fill ORDER BY seq"
    ).fetchall()
    return [
        Fill(
            side=Side(r[1]),
            price=Decimal(r[2]),
            shares=r[3],
            fee=Decimal(r[4]),
            level_index=r[5],
            ts=datetime.fromisoformat(r[0]) if r[0] else None,
            realized_pnl=Decimal(r[6]) if r[6] is not None else None,
        )
        for r in rows
    ]
