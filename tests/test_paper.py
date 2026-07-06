"""模拟盘 runner 测试（FakeProvider 不打网，用 process_tick 直接驱动）。"""

from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.core import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.paper.runner import PaperRunner
from vgrid.paper.session import in_session, next_session_open
from vgrid.store import connect, load_fills, load_ticks


def _zero_config() -> GridConfig:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )


class _FakeProvider:
    """测试不通过 fetch 驱动（直接调 process_tick）。"""

    def fetch(self, symbol: str) -> tuple[datetime, Decimal]:
        raise NotImplementedError("测试用 process_tick 直接驱动")


def test_first_tick_starts_engine_without_fills() -> None:
    conn = connect()
    runner = PaperRunner(_zero_config(), _FakeProvider(), conn)
    runner.replay()  # 空历史
    assert runner.process_tick(datetime(2024, 1, 2, 9, 30), Decimal("1.10")) == []
    assert len(load_ticks(conn)) == 1


def test_center_build_persists_buildup_fills() -> None:
    """中枢建仓：首个 tick 的 start 成交也要落库。"""
    conn = connect()
    cfg = GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.20"),
        grid_count=4,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
    )  # 默认 CENTER
    runner = PaperRunner(cfg, _FakeProvider(), conn)
    runner.replay()
    fills = runner.process_tick(datetime(2024, 1, 2, 9, 30), Decimal("1.10"))
    assert len(fills) >= 1  # 上方两格底仓
    assert len(load_fills(conn)) == len(fills)  # 全部落库


def test_process_tick_drives_buys_and_persists() -> None:
    conn = connect()
    runner = PaperRunner(_zero_config(), _FakeProvider(), conn)
    runner.replay()
    runner.process_tick(datetime(2024, 1, 2, 9, 30), Decimal("1.10"))
    fills = runner.process_tick(datetime(2024, 1, 2, 9, 31), Decimal("1.05"))  # 跌触发买

    assert len(fills) == 1
    assert len(load_ticks(conn)) == 2
    assert len(load_fills(conn)) == 1


def test_replay_rebuilds_engine_state() -> None:
    """新 runner 读同一 DB 的 tick replay，engine 状态应与原 runner 末态一致。"""
    conn = connect()
    runner1 = PaperRunner(_zero_config(), _FakeProvider(), conn)
    runner1.replay()
    runner1.process_tick(datetime(2024, 1, 2, 9, 30), Decimal("1.10"))
    runner1.process_tick(datetime(2024, 1, 2, 9, 31), Decimal("1.05"))
    runner1.process_tick(datetime(2024, 1, 2, 9, 32), Decimal("1.00"))  # 再买一格
    snap1 = runner1.snapshot()

    runner2 = PaperRunner(_zero_config(), _FakeProvider(), conn)
    runner2.replay()
    assert runner2.snapshot() == snap1


def test_rejects_mismatched_config() -> None:
    conn = connect()
    PaperRunner(_zero_config(), _FakeProvider(), conn)
    other = GridConfig(
        symbol="159920",
        lower_price=Decimal("1.00"),
        upper_price=Decimal("1.30"),
        grid_count=6,
        per_grid_amount=Decimal("2000"),
        capital_cap=Decimal("50000"),
        base_build_mode=BaseBuildMode.ZERO,
    )
    with pytest.raises(ValueError, match="不同配置"):
        PaperRunner(other, _FakeProvider(), conn)


def test_in_session_during_trading_hours() -> None:
    assert in_session(datetime(2024, 1, 2, 10, 0)) is True  # 周二上午
    assert in_session(datetime(2024, 1, 2, 14, 30)) is True  # 周二下午


def test_in_session_outside_trading_hours() -> None:
    assert in_session(datetime(2024, 1, 2, 9, 0)) is False  # 盘前
    assert in_session(datetime(2024, 1, 2, 12, 0)) is False  # 午休
    assert in_session(datetime(2024, 1, 2, 16, 0)) is False  # 盘后
    assert in_session(datetime(2024, 1, 6, 10, 0)) is False  # 周六


def test_next_session_open() -> None:
    assert next_session_open(datetime(2024, 1, 2, 9, 0)) == datetime(2024, 1, 2, 9, 30)
    assert next_session_open(datetime(2024, 1, 2, 12, 0)) == datetime(2024, 1, 2, 13, 0)
    assert next_session_open(datetime(2024, 1, 2, 16, 0)) == datetime(2024, 1, 3, 9, 30)
    assert next_session_open(datetime(2024, 1, 5, 16, 0)) == datetime(
        2024, 1, 8, 9, 30
    )  # 周五→周一
    assert next_session_open(datetime(2024, 1, 6, 10, 0)) == datetime(
        2024, 1, 8, 9, 30
    )  # 周六→周一
