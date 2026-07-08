"""SQLite 存取测试（内存库）。"""

import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.core import GridConfig
from vgrid.core.enums import Side
from vgrid.core.models import Fill
from vgrid.store import (
    connect,
    load_config,
    load_fills,
    load_ticks,
    save_config,
    save_fill,
    save_tick,
    save_tick_with_fills,
)


def _cfg() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )


def test_config_roundtrip() -> None:
    conn = connect()
    assert load_config(conn) is None
    save_config(conn, _cfg())
    assert load_config(conn) == _cfg()


def test_config_upsert_replaces() -> None:
    conn = connect()
    save_config(conn, _cfg())
    other = GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.30"),
        grid_count=6,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )
    save_config(conn, other)
    assert load_config(conn) == other


def test_tick_roundtrip_preserves_arrival_order() -> None:
    """按 seq（到达顺序）回放，不按 ts 排序——时钟回拨也不会乱序（review #22）。"""
    conn = connect()
    save_tick(conn, datetime(2024, 1, 2, 9, 31), Decimal("1.005"))
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.000"))  # ts 更早但后到
    ticks = load_ticks(conn)
    assert ticks == [
        (datetime(2024, 1, 2, 9, 31), Decimal("1.005")),
        (datetime(2024, 1, 2, 9, 30), Decimal("1.000")),
    ]


def test_tick_decimal_precision_preserved() -> None:
    conn = connect()
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.0573"))
    assert load_ticks(conn)[0][1] == Decimal("1.0573")


def test_tick_same_ts_keeps_both() -> None:
    """同 ts 不再覆盖——seq 自增主键，两笔都保留（review #22）。"""
    conn = connect()
    ts = datetime(2024, 1, 2, 9, 30)
    save_tick(conn, ts, Decimal("1.000"))
    save_tick(conn, ts, Decimal("1.005"))
    ticks = load_ticks(conn)
    assert len(ticks) == 2
    assert [t[1] for t in ticks] == [Decimal("1.000"), Decimal("1.005")]


def test_save_tick_with_fills_atomic() -> None:
    """tick + fills 单事务：全进或全不进（review #21）。"""
    conn = connect()
    ts = datetime(2024, 1, 2, 9, 30)
    fills = [
        Fill(Side.BUY, Decimal("1.00"), 100, Decimal("0.10"), 2, ts=ts),
        Fill(
            Side.SELL, Decimal("1.10"), 100, Decimal("0.10"), 3, ts=ts,
            realized_pnl=Decimal("9.80"),
        ),
    ]
    save_tick_with_fills(conn, ts, Decimal("1.005"), fills)
    assert len(load_ticks(conn)) == 1
    assert len(load_fills(conn)) == 2


def test_fill_unique_rejects_duplicate() -> None:
    """同一 (ts,side,price,shares,level_index) 重复插入被 UNIQUE 挡下（review #35）。"""
    conn = connect()
    ts = datetime(2024, 1, 2, 9, 30)
    f = Fill(Side.BUY, Decimal("1.00"), 100, Decimal("0.10"), 2, ts=ts)
    save_fill(conn, f)
    with pytest.raises(sqlite3.IntegrityError):
        save_fill(conn, f)


def test_fill_roundtrip_with_pnl() -> None:
    conn = connect()
    f = Fill(
        Side.SELL,
        Decimal("1.10"),
        100,
        Decimal("0.10"),
        2,
        ts=datetime(2024, 1, 2, 9, 31),
        realized_pnl=Decimal("9.90"),
    )
    save_fill(conn, f)
    loaded = load_fills(conn)
    assert len(loaded) == 1
    assert loaded[0] == f


def test_fill_buy_without_pnl() -> None:
    conn = connect()
    f = Fill(
        Side.BUY,
        Decimal("1.00"),
        100,
        Decimal("0.10"),
        2,
        ts=datetime(2024, 1, 2, 9, 30),
    )
    save_fill(conn, f)
    loaded = load_fills(conn)
    assert loaded[0] == f
    assert loaded[0].realized_pnl is None


def test_fills_ordered_by_seq() -> None:
    conn = connect()
    first = Fill(Side.BUY, Decimal("1.00"), 100, Decimal("0.10"), 2, ts=datetime(2024, 1, 2, 9, 30))
    second = Fill(
        Side.SELL,
        Decimal("1.10"),
        100,
        Decimal("0.10"),
        2,
        ts=datetime(2024, 1, 2, 10, 0),
        realized_pnl=Decimal("9.80"),
    )
    save_fill(conn, first)
    save_fill(conn, second)
    loaded = load_fills(conn)
    assert [f.side for f in loaded] == [Side.BUY, Side.SELL]
