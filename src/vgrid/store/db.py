"""SQLite 连接 + schema。

一个模拟盘一份 DB。三张表：``config``（策略配置，单行 id=1）、``tick``（实时 tick 历史）、
``fill``（成交历史）。金额 / 价格以 string 存（``Decimal`` 无损），ts 以 ISO 字符串存；
读写转换在 ``repository`` 里。

tick 用自增 ``seq`` 做主键（而非 wall-clock ts）——replay 按到达顺序（seq）回放，不受
时钟回拨 / 同 ts 撞车影响（review #22）。fill 加自然键 UNIQUE 做防御纵深（review #35）。
"""

from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    id    INTEGER PRIMARY KEY CHECK (id = 1),
    json  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tick (
    seq    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    price  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fill (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    side          TEXT NOT NULL,
    price         TEXT NOT NULL,
    shares        INTEGER NOT NULL,
    fee           TEXT NOT NULL,
    level_index   INTEGER NOT NULL,
    realized_pnl  TEXT,
    UNIQUE(ts, side, price, shares, level_index)
);
"""


def apply_pragmas(conn: sqlite3.Connection) -> None:
    """给文件库设并发 pragma：WAL（读写不互斥）+ busy_timeout（锁等待 5s 而非立刻报错）。

    review #31：默认 ``sqlite3.connect`` 的 busy_timeout 是 5s，但没设 WAL；多 writer
    （paper run 写、paper serve 读、portfolio 聚合）并发时容易 ``database is locked``。
    内存库无需 WAL（单连接），但调一下也无害。
    """
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """打开 / 建库并确保 schema 存在。默认内存库（测试用）；生产给文件路径。

    文件库开 WAL：``paper run`` 写、``paper serve`` 读两个进程并发时读不阻塞写。
    """
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    if path != ":memory:":
        apply_pragmas(conn)
    return conn
