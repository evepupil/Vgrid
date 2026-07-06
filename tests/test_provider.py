"""列式数据转 Bar 的纯函数测试（不碰 pandas / akshare）。"""

from datetime import datetime
from decimal import Decimal

import pytest

from vgrid.core.enums import Frame
from vgrid.data.provider import bars_from_columns


def test_columns_to_bars_basic() -> None:
    columns = {
        "ts": ["2024-01-02", "2024-01-03"],
        "open": ["1.00", "1.01"],
        "high": ["1.05", "1.06"],
        "low": ["0.99", "1.00"],
        "close": ["1.03", "1.04"],
        "volume": ["100", "200"],
    }
    bars = bars_from_columns(columns, Frame.DAILY)
    assert len(bars) == 2
    assert bars[0].ts == datetime(2024, 1, 2)
    assert bars[0].close == Decimal("1.03")
    assert bars[1].volume == Decimal("200")


def test_columns_sorted_by_ts() -> None:
    """乱序输入应按 ts 升序返回。"""
    columns = {
        "ts": ["2024-01-03", "2024-01-02"],
        "open": ["1.01", "1.00"],
        "high": ["1.06", "1.05"],
        "low": ["1.00", "0.99"],
        "close": ["1.04", "1.03"],
        "volume": ["200", "100"],
    }
    bars = bars_from_columns(columns, Frame.DAILY)
    assert [b.ts for b in bars] == [datetime(2024, 1, 2), datetime(2024, 1, 3)]
    assert bars[0].open == Decimal("1.00")


def test_columns_minute_ts_parsed() -> None:
    columns = {
        "ts": ["2024-01-02 09:31:00"],
        "open": ["1.00"],
        "high": ["1.01"],
        "low": ["0.99"],
        "close": ["1.00"],
        "volume": ["50"],
    }
    bars = bars_from_columns(columns, Frame.MINUTE)
    assert bars[0].ts == datetime(2024, 1, 2, 9, 31)


def test_columns_reject_missing_field() -> None:
    columns = {
        "ts": ["2024-01-02"],
        "open": ["1"],
        "high": ["1"],
        "low": ["1"],
        "close": ["1"],
    }
    with pytest.raises(ValueError, match="缺少字段"):
        bars_from_columns(columns, Frame.DAILY)


def test_columns_reject_length_mismatch() -> None:
    columns = {
        "ts": ["2024-01-02", "2024-01-03"],
        "open": ["1"],
        "high": ["1", "1"],
        "low": ["1", "1"],
        "close": ["1", "1"],
        "volume": ["1", "1"],
    }
    with pytest.raises(ValueError, match="长度不一致"):
        bars_from_columns(columns, Frame.DAILY)


def test_columns_accept_datetime_and_numeric() -> None:
    """ts 接受 datetime，价格接受数字。"""
    columns: dict[str, list[object]] = {
        "ts": [datetime(2024, 1, 2)],
        "open": [1.0],
        "high": [1.0],
        "low": [1.0],
        "close": [1.0],
        "volume": [0],
    }
    bars = bars_from_columns(columns, Frame.DAILY)
    assert bars[0].open == Decimal("1.0")
