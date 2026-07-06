"""strategy_store 纯逻辑测试（tmp_path 临时目录，不碰网络）。"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from vgrid.core.config import GridConfig
from vgrid.web.strategy_store import (
    delete_strategy,
    list_strategies,
    read_strategy,
    write_strategy,
)


def _config_dict() -> dict[str, object]:
    return GridConfig(
        symbol="159920",
        lower_price=Decimal("0.976"),
        upper_price=Decimal("1.024"),
        grid_count=16,
        per_grid_amount=Decimal("3000"),
        capital_cap=Decimal("50000"),
    ).to_dict()


def test_list_empty_when_dir_missing(tmp_path: Path) -> None:
    assert list_strategies(tmp_path / "nope") == []


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    write_strategy(tmp_path, "恒生网格", _config_dict())
    data = read_strategy(tmp_path, "恒生网格")
    assert data["symbol"] == "159920"
    assert data["grid_count"] == 16


def test_list_returns_summary_sorted(tmp_path: Path) -> None:
    write_strategy(tmp_path, "b", _config_dict())
    write_strategy(tmp_path, "a", _config_dict())
    names = [s.name for s in list_strategies(tmp_path)]
    assert names == ["a", "b"]
    s = list_strategies(tmp_path)[0]
    assert s.symbol == "159920"
    assert s.spacing_mode == "arithmetic"


def test_read_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_strategy(tmp_path, "nope")


def test_invalid_name_rejected(tmp_path: Path) -> None:
    for name in ("../etc", "a/b", "a\\b", "", "a b", "a.b"):
        with pytest.raises(ValueError):
            write_strategy(tmp_path, name, _config_dict())


def test_write_validates_config(tmp_path: Path) -> None:
    bad = _config_dict()
    bad["grid_count"] = 0  # < 1 非法
    with pytest.raises(ValueError):
        write_strategy(tmp_path, "bad", bad)


def test_delete(tmp_path: Path) -> None:
    write_strategy(tmp_path, "a", _config_dict())
    assert delete_strategy(tmp_path, "a") is True
    assert delete_strategy(tmp_path, "a") is False  # 幂等


def test_delete_invalid_name_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        delete_strategy(tmp_path, "../x")


def test_bad_file_skipped_in_list(tmp_path: Path) -> None:
    write_strategy(tmp_path, "good", _config_dict())
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    names = [s.name for s in list_strategies(tmp_path)]
    assert names == ["good"]  # 坏文件跳过
