"""DcaConfig 序列化 + 校验 + 金额规则解析测试。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from vgrid.dca.config import AmountMode, DcaConfig, Frequency


def _fixed() -> dict[str, object]:
    return {
        "type": "dca",
        "symbol": "159920",
        "frequency": "weekly",
        "weekday": 1,
        "base_amount": "2000",
        "cash_cap": "50000",
        "amount_policy": {"mode": "fixed"},
    }


def test_from_dict_fixed() -> None:
    cfg = DcaConfig.from_dict(_fixed())
    assert cfg.symbol == "159920"
    assert cfg.frequency is Frequency.WEEKLY
    assert cfg.base_amount == Decimal("2000")
    assert cfg.amount_policy.mode is AmountMode.FIXED
    assert cfg.start_cash == Decimal("50000")  # 未给 initial_cash → 用 cash_cap


def test_roundtrip_drawdown() -> None:
    data = _fixed()
    data["amount_policy"] = {
        "mode": "drawdown",
        "lookback_days": 120,
        "tiers": [
            {"drawdown": "0.05", "multiplier": "1.0"},
            {"drawdown": "0.10", "multiplier": "1.5"},
        ],
    }
    cfg = DcaConfig.from_dict(data)
    assert cfg.amount_policy.mode is AmountMode.DRAWDOWN
    assert len(cfg.amount_policy.tiers) == 2
    # to_dict → from_dict 往返一致
    again = DcaConfig.from_dict(cfg.to_dict())
    assert again.amount_policy.tiers == cfg.amount_policy.tiers
    assert again.to_dict() == cfg.to_dict()


def test_roundtrip_ma_deviation() -> None:
    data = _fixed()
    data["amount_policy"] = {
        "mode": "ma_deviation",
        "ma_window": 60,
        "below_multiplier": "1.5",
        "above_multiplier": "0.3",
    }
    cfg = DcaConfig.from_dict(data)
    assert cfg.amount_policy.mode is AmountMode.MA_DEVIATION
    assert cfg.amount_policy.ma_window == 60
    assert cfg.amount_policy.above_multiplier == Decimal("0.3")
    assert DcaConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()


def test_drawdown_requires_tiers() -> None:
    data = _fixed()
    data["amount_policy"] = {"mode": "drawdown", "tiers": []}
    with pytest.raises(ValueError, match="至少要有一档"):
        DcaConfig.from_dict(data)


def test_rejects_bad_weekday() -> None:
    data = _fixed()
    data["weekday"] = 8
    with pytest.raises(ValueError, match="weekday"):
        DcaConfig.from_dict(data)


def test_rejects_nonpositive_amounts() -> None:
    data = _fixed()
    data["base_amount"] = "0"
    with pytest.raises(ValueError, match="每次投入"):
        DcaConfig.from_dict(data)
