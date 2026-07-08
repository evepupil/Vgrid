"""金额规则测试：固定 / 跌幅加码 / 均线偏离（纯函数）。"""

from __future__ import annotations

from decimal import Decimal

from vgrid.dca.amount import amount_for
from vgrid.dca.config import AmountMode, AmountPolicy, DrawdownTier

_BASE = Decimal("2000")


def test_fixed_is_constant() -> None:
    p = AmountPolicy(mode=AmountMode.FIXED)
    assert amount_for(p, _BASE, [], Decimal("9")) == _BASE
    assert amount_for(p, _BASE, [Decimal("10")], Decimal("5")) == _BASE


def _drawdown_policy() -> AmountPolicy:
    return AmountPolicy(
        mode=AmountMode.DRAWDOWN,
        lookback_days=10,
        tiers=(
            DrawdownTier(Decimal("0.05"), Decimal("1")),
            DrawdownTier(Decimal("0.10"), Decimal("1.5")),
            DrawdownTier(Decimal("0.20"), Decimal("2")),
        ),
    )


def test_drawdown_takes_highest_applicable_tier() -> None:
    p = _drawdown_policy()
    highs = [Decimal("10")] * 5
    assert amount_for(p, _BASE, highs, Decimal("9")) == _BASE * Decimal("1.5")  # 回撤 10%
    assert amount_for(p, _BASE, highs, Decimal("8")) == _BASE * Decimal("2")  # 回撤 20%


def test_drawdown_no_tier_hit_is_base() -> None:
    p = _drawdown_policy()
    highs = [Decimal("10")] * 5
    assert amount_for(p, _BASE, highs, Decimal("9.8")) == _BASE  # 回撤 2%，够不上第一档


def test_drawdown_no_history_is_base() -> None:
    p = _drawdown_policy()
    assert amount_for(p, _BASE, [], Decimal("8")) == _BASE  # 没历史高点 → 1 倍


def _ma_policy() -> AmountPolicy:
    return AmountPolicy(
        mode=AmountMode.MA_DEVIATION,
        ma_window=3,
        below_multiplier=Decimal("1.5"),
        normal_multiplier=Decimal("1"),
        above_multiplier=Decimal("0.5"),
    )


def test_ma_below_amplifies() -> None:
    p = _ma_policy()
    closes = [Decimal("10")] * 3  # ma=10
    assert amount_for(p, _BASE, closes, Decimal("9")) == _BASE * Decimal("1.5")


def test_ma_above_shrinks() -> None:
    p = _ma_policy()
    closes = [Decimal("10")] * 3
    assert amount_for(p, _BASE, closes, Decimal("11")) == _BASE * Decimal("0.5")


def test_ma_insufficient_history_is_base() -> None:
    p = _ma_policy()
    assert amount_for(p, _BASE, [Decimal("10"), Decimal("10")], Decimal("9")) == _BASE
