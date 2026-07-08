"""CLI 错误处理测试（review #9）：已知异常收成退出码 1，不把 traceback 糊给用户。

配置 / 规格解析都在下载行情之前，所以这些用例不打网络。
"""

import json
from pathlib import Path

import pytest

from vgrid.cli.app import main


def _backtest_args(config: Path) -> list[str]:
    return [
        "backtest",
        "--symbol",
        "159920",
        "--start",
        "2024-01-02",
        "--end",
        "2024-01-03",
        "--config",
        str(config),
    ]


def test_backtest_missing_config_file_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(_backtest_args(tmp_path / "nope.json"))
    assert rc == 1
    assert "错误" in capsys.readouterr().err


def test_backtest_invalid_config_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"symbol": "159920"}), encoding="utf-8")  # 缺必填字段
    rc = main(_backtest_args(bad))
    assert rc == 1
    assert "错误" in capsys.readouterr().err


def _dca_args(config: Path) -> list[str]:
    return [
        "dca",
        "--symbol",
        "159920",
        "--start",
        "2024-01-02",
        "--end",
        "2024-01-03",
        "--config",
        str(config),
    ]


def test_dca_missing_config_file_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(_dca_args(tmp_path / "nope.json"))
    assert rc == 1
    assert "错误" in capsys.readouterr().err


def test_dca_invalid_config_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"symbol": "159920"}), encoding="utf-8")  # 缺 frequency 等必填
    rc = main(_dca_args(bad))
    assert rc == 1
    assert "错误" in capsys.readouterr().err


def test_compare_needs_a_config_returns_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 两个配置都不给 → 下载前就退 1（不打网）
    rc = main(
        ["compare", "--symbol", "159920", "--start", "2024-01-02", "--end", "2024-01-03"]
    )
    assert rc == 1
    assert "至少" in capsys.readouterr().err


def test_scan_missing_spec_file_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "scan",
            "--symbol",
            "159920",
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-03",
            "--spec",
            str(tmp_path / "nope.json"),
        ]
    )
    assert rc == 1
    assert "错误" in capsys.readouterr().err
