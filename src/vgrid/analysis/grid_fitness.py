"""网格适配评分（0–100）：给一串日线，判断它多适合跑网格。纯函数，单测重点。

一句话原理：**网格吃震荡、怕单边趋势**。同样的涨跌幅，来回震荡能让网格反复低买高卖赚
差价；一路单边涨/跌只成交一次，网格反而跑输买入持有。所以评分把「来回震荡」当加分、
「单边趋势」当减分。

三个可解释的量（都只用加减除，不碰 float / sqrt，Decimal 全程无损）：

- **振幅 amplitude**：平均每日 ``(最高−最低)/昨收``（%）。没有振幅就没有网格利润来源，
  低了扣分。
- **趋势度 trendiness**：Kaufman 效率比 ``|净涨跌| / Σ|逐日涨跌|`` ∈ [0,1]。1 = 一路
  单边（净移动等于路径全长），0 = 纯来回（净移动为 0）。越大越不适合网格。
- **穿越次数 crossings**：收盘价上下穿越自身均线的次数。穿得越多越震荡，加分。

合成（先给个能用的公式，后续用回测校准权重）：
``score = 100 × (0.5×(1−趋势度) + 0.3×振幅因子 + 0.2×穿越因子)``，钳到 [0,100] 取整。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from vgrid.core.bar import Bar

# —— 可调常数（后续回测校准）——
MIN_BARS = 10  # 少于这么多根不给分（样本太小没意义）
TARGET_AMPLITUDE_PCT = Decimal("2.0")  # 平均日振幅达到 2% 视作「网格燃料充足」，封顶
_W_OSC = Decimal("0.5")  # 震荡（非趋势）权重
_W_AMP = Decimal("0.3")  # 振幅权重
_W_CROSS = Decimal("0.2")  # 穿越权重
_CROSS_DIVISOR = Decimal("4")  # 穿越因子归一：穿越 ≥ n/4 次即封顶


@dataclass(frozen=True, slots=True)
class GridFitness:
    """网格适配评分及其可解释分项。"""

    score: int  # 0–100
    amplitude_pct: Decimal  # 平均日振幅（%）
    trendiness: Decimal  # 效率比 [0,1]，越大越单边
    crossings: int  # 收盘穿越均线次数
    n_bars: int  # 参与计算的根数


def grid_fitness(bars: Sequence[Bar]) -> GridFitness | None:
    """算一串日线的网格适配评分。根数不足 ``MIN_BARS`` 返回 ``None``。"""
    if len(bars) < MIN_BARS:
        return None
    closes = [b.close for b in bars]
    amp = _amplitude_pct(bars)
    trend = _trendiness(closes)
    cross = _crossings(closes)

    osc_factor = Decimal(1) - trend  # 越不趋势越高
    amp_factor = _clamp01(amp / TARGET_AMPLITUDE_PCT)
    cross_cap = Decimal(len(bars)) / _CROSS_DIVISOR
    cross_factor = _clamp01(Decimal(cross) / cross_cap) if cross_cap > 0 else Decimal(0)

    raw = _W_OSC * osc_factor + _W_AMP * amp_factor + _W_CROSS * cross_factor
    score = int((raw * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    return GridFitness(
        score=max(0, min(100, score)),
        amplitude_pct=amp,
        trendiness=trend,
        crossings=cross,
        n_bars=len(bars),
    )


def _amplitude_pct(bars: Sequence[Bar]) -> Decimal:
    """平均每日 ``(high−low)/昨收`` × 100。第一根无昨收，跳过。"""
    ratios: list[Decimal] = []
    for prev, cur in pairwise(bars):
        if prev.close > 0:
            ratios.append((cur.high - cur.low) / prev.close)
    if not ratios:
        return Decimal(0)
    return sum(ratios, Decimal(0)) / Decimal(len(ratios)) * 100


def _trendiness(closes: Sequence[Decimal]) -> Decimal:
    """Kaufman 效率比：``|收盘首末差| / Σ|逐日收盘差|``，∈ [0,1]。

    路径全长为 0（收盘全程不动）时返回 1——不动没有震荡收益，按最不适合网格处理。
    """
    net = abs(closes[-1] - closes[0])
    path = sum((abs(b - a) for a, b in pairwise(closes)), Decimal(0))
    if path == 0:
        return Decimal(1)
    return _clamp01(net / path)


def _crossings(closes: Sequence[Decimal]) -> int:
    """收盘价上下穿越自身均线的次数（正负号翻转计一次）。"""
    mean = sum(closes, Decimal(0)) / Decimal(len(closes))
    prev_sign = 0
    count = 0
    for c in closes:
        diff = c - mean
        sign = 1 if diff > 0 else (-1 if diff < 0 else 0)
        if sign != 0 and prev_sign not in (0, sign):
            count += 1
        if sign != 0:
            prev_sign = sign
    return count


def _clamp01(v: Decimal) -> Decimal:
    return max(Decimal(0), min(Decimal(1), v))
