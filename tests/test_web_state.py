"""web/state load_state 测试（内存库）。"""

from datetime import datetime
from decimal import Decimal
from sqlite3 import Connection

from vgrid.core import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.store import connect, save_config, save_tick
from vgrid.web.state import load_state


def _cfg() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


def _seed(conn: Connection) -> None:
    save_config(conn, _cfg())
    save_tick(conn, datetime(2024, 1, 2, 9, 30), Decimal("1.10"))
    save_tick(conn, datetime(2024, 1, 2, 9, 31), Decimal("1.05"))
    save_tick(conn, datetime(2024, 1, 2, 9, 32), Decimal("1.10"))


def test_load_state_none_when_no_config() -> None:
    assert load_state(connect()) is None


def test_load_state_basic() -> None:
    conn = connect()
    _seed(conn)
    view = load_state(conn)
    assert view is not None
    assert view.symbol == "159920"
    assert view.n_ticks == 3
    assert len(view.equity_curve) == 3  # 3 <= 300，不降采样
    assert "open_lots" in view.snapshot


def test_downsample_caps_curve_length() -> None:
    conn = connect()
    _seed(conn)
    for i in range(400):
        save_tick(conn, datetime(2024, 1, 2, 10, i % 60), Decimal("1.05"))
    view = load_state(conn, curve_points=50)
    assert view is not None
    assert len(view.equity_curve) <= 50


def test_fill_marks_within_curve() -> None:
    conn = connect()
    _seed(conn)  # ZERO: start 无成交，step(1.05) 买，step(1.10) 卖
    view = load_state(conn)
    assert view is not None
    assert len(view.fill_marks) >= 1
    for m in view.fill_marks:
        assert 0 <= m.index < len(view.equity_curve)


def test_metrics_populated() -> None:
    conn = connect()
    _seed(conn)
    view = load_state(conn)
    assert view is not None
    for key in ("total_return", "max_drawdown", "sharpe", "buy_hold_return"):
        assert key in view.metrics
