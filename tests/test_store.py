"""SQLite 存取测试（内存库）。"""

from datetime import datetime
from decimal import Decimal

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


def test_tick_roundtrip_and_order() -> None:
    conn = connect()
    save_tick(conn, datetime(2024, 1, 2, 9, 31), Decimal("1.005"))
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.000"))  # 乱序插入
    ticks = load_ticks(conn)
    assert ticks == [
        (datetime(2024, 1, 2, 9, 30), Decimal("1.000")),
        (datetime(2024, 1, 2, 9, 31), Decimal("1.005")),
    ]


def test_tick_decimal_precision_preserved() -> None:
    conn = connect()
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.0573"))
    assert load_ticks(conn)[0][1] == Decimal("1.0573")


def test_tick_same_ts_replaces() -> None:
    conn = connect()
    ts = datetime(2024, 1, 2, 9, 30)
    save_tick(conn, ts, Decimal("1.000"))
    save_tick(conn, ts, Decimal("1.005"))  # 同 ts 覆盖
    assert len(load_ticks(conn)) == 1
    assert load_ticks(conn)[0][1] == Decimal("1.005")


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
