"""每次投多少：三种金额规则的纯计算。

信号一律只用**执行 K 线之前**的收盘价（``prior_closes``），当前价用执行 K 线的
``open``（买入价，成交时已知）——这样即便信号里带了当前价，也没偷看未来（不碰当根
high/low/close）。三种规则：
- 固定：恒为 ``base_amount``。
- 跌幅加码：近期高点回撤越大，取「满足的最高档」倍数。
- 均线偏离：现价低于均线放大、高于均线缩小。
"""

from __future__ import annotations

from decimal import Decimal

from vgrid.dca.config import AmountMode, AmountPolicy


def amount_for(
    policy: AmountPolicy,
    base_amount: Decimal,
    prior_closes: list[Decimal],
    price: Decimal,
) -> Decimal:
    """按规则算出本次「想投多少」（还没受现金 / 上限约束、没取整）。"""
    if policy.mode is AmountMode.FIXED:
        return base_amount
    if policy.mode is AmountMode.DRAWDOWN:
        return base_amount * _drawdown_multiplier(policy, prior_closes, price)
    return base_amount * _ma_multiplier(policy, prior_closes, price)


def _drawdown_multiplier(
    policy: AmountPolicy, prior_closes: list[Decimal], price: Decimal
) -> Decimal:
    """近期高点回撤 → 满足的最高档倍数；历史不足 / 无回撤则 1 倍。"""
    window = prior_closes[-policy.lookback_days :]
    if not window:
        return Decimal(1)
    recent_high = max(window)
    if recent_high <= 0:
        return Decimal(1)
    drawdown = (recent_high - price) / recent_high
    multiplier = Decimal(1)
    for tier in policy.sorted_tiers:  # 升序，取满足的最高档
        if drawdown >= tier.drawdown:
            multiplier = tier.multiplier
    return multiplier


def _ma_multiplier(policy: AmountPolicy, prior_closes: list[Decimal], price: Decimal) -> Decimal:
    """现价 vs 均线 → 低于放大 / 高于缩小 / 持平不变；历史不足则 1 倍。"""
    if len(prior_closes) < policy.ma_window:
        return Decimal(1)
    window = prior_closes[-policy.ma_window :]
    ma = sum(window, Decimal(0)) / Decimal(len(window))
    if price < ma:
        return policy.below_multiplier
    if price > ma:
        return policy.above_multiplier
    return policy.normal_multiplier
