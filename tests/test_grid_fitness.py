"""网格适配评分纯函数测试：趋势低分、震荡高分、样本量守卫、分项单调性。"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal

from vgrid.analysis.grid_fitness import MIN_BARS, grid_fitness
from vgrid.core.bar import Bar


def _bar(offset: int, close: float, *, amp: float = 0.01) -> Bar:
    """按收盘价造一根日线，高低围绕收盘上下各 amp/2（保证 OHLC 互检通过）。"""
    c = Decimal(str(round(close, 4)))
    half = Decimal(str(round(close * amp / 2, 4)))
    return Bar(
        ts=datetime(2024, 1, 1) + timedelta(days=offset),
        open=c,
        high=c + half,
        low=c - half,
        close=c,
        volume=Decimal("100"),
    )


def _series(closes: list[float], *, amp: float = 0.01) -> list[Bar]:
    return [_bar(i, c, amp=amp) for i, c in enumerate(closes)]


def test_too_few_bars_returns_none() -> None:
    assert grid_fitness(_series([1.0] * (MIN_BARS - 1))) is None


def test_monotonic_uptrend_scores_low() -> None:
    # 一路单边上涨：效率比≈1，网格最不适合
    up = _series([1.0 + i * 0.01 for i in range(60)])
    gf = grid_fitness(up)
    assert gf is not None
    assert gf.trendiness > Decimal("0.95")
    assert gf.score < 40


def test_choppy_sideways_scores_high() -> None:
    # 来回震荡、有振幅：效率比低、穿越多、振幅够，网格最适合
    closes = [1.0 + 0.05 * math.sin(i / 2.0) for i in range(60)]
    gf = grid_fitness(_series(closes, amp=0.025))
    assert gf is not None
    assert gf.trendiness < Decimal("0.3")
    assert gf.crossings > 5
    assert gf.score > 65


def test_choppy_beats_trend() -> None:
    trend = grid_fitness(_series([1.0 + i * 0.01 for i in range(60)], amp=0.025))
    chop = grid_fitness(_series([1.0 + 0.05 * math.sin(i / 2.0) for i in range(60)], amp=0.025))
    assert trend is not None and chop is not None
    assert chop.score > trend.score


def test_flat_dead_scores_low() -> None:
    # 完全不动：无振幅无震荡收益，趋势度按 1 处理，评分很低
    gf = grid_fitness(_series([1.0] * 60, amp=0.0))
    assert gf is not None
    assert gf.trendiness == Decimal("1")
    assert gf.amplitude_pct == Decimal("0")
    assert gf.score < 10


def test_amplitude_pct_reasonable() -> None:
    # 每日高低差约 2%（amp=0.02）→ 平均振幅≈2%
    gf = grid_fitness(_series([1.0 + 0.03 * math.sin(i) for i in range(60)], amp=0.02))
    assert gf is not None
    assert Decimal("1.5") < gf.amplitude_pct < Decimal("2.6")


def test_score_within_bounds() -> None:
    for closes in ([1.0 + i for i in range(30)], [1.0] * 30, [1.0, 2.0] * 15):
        gf = grid_fitness(_series(closes, amp=0.03))
        assert gf is not None
        assert 0 <= gf.score <= 100
