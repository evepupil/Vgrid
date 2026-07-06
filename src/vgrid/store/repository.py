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
    """同 ts 覆盖（INSERT OR REPLACE）。"""
    conn.execute(
        "INSERT OR REPLACE INTO tick(ts, price) VALUES (?, ?)",
        (ts.isoformat(), str(price)),
    )
    conn.commit()


def load_ticks(conn: sqlite3.Connection) -> list[tuple[datetime, Decimal]]:
    """按 ts 升序返回全部 tick。"""
    rows = conn.execute("SELECT ts, price FROM tick ORDER BY ts").fetchall()
    return [(datetime.fromisoformat(r[0]), Decimal(r[1])) for r in rows]


def save_fill(conn: sqlite3.Connection, fill: Fill) -> None:
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
    conn.commit()


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
