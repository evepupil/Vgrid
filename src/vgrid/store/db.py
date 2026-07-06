"""SQLite 连接 + schema。

一个模拟盘一份 DB。三张表：``config``（策略配置，单行 id=1）、``tick``（实时 tick 历史）、
``fill``（成交历史）。金额 / 价格以 string 存（``Decimal`` 无损），ts 以 ISO 字符串存；
读写转换在 ``repository`` 里。
"""

from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    id    INTEGER PRIMARY KEY CHECK (id = 1),
    json  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tick (
    ts    TEXT PRIMARY KEY,
    price TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fill (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    side          TEXT NOT NULL,
    price         TEXT NOT NULL,
    shares        INTEGER NOT NULL,
    fee           TEXT NOT NULL,
    level_index   INTEGER NOT NULL,
    realized_pnl  TEXT
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """打开 / 建库并确保 schema 存在。默认内存库（测试用）；生产给文件路径。

    文件库开 WAL：``paper run`` 写、``paper serve`` 读两个进程并发时读不阻塞写。
    """
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn
