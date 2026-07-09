"""红利增强组合回测测试：分红再投 overlay + 定投 / 网格便捷封装。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.core.fees import FeeModel
from vgrid.dca.config import DcaConfig, Frequency
from vgrid.income.combo import (
    dca_dividend_combo,
    dividend_reinvest_overlay,
    grid_dividend_combo,
)
from vgrid.income.models import DividendEvent

_FEE = FeeModel()


def _bar(day: date, open_: str, close: str) -> Bar:
    o, c = Decimal(open_), Decimal(close)
    return Bar(ts=datetime(day.year, day.month, day.day), open=o, high=max(o, c),
               low=min(o, c), close=c, volume=Decimal("1000"))


def _flat_bars(n: int) -> list[Bar]:
    return [_bar(date(2024, 1, 2 + i), "1.00", "1.00") for i in range(n)]


def _hold_curve(bars: list[Bar], shares: int) -> list[EquityPoint]:
    """构造「恒定持仓 shares、无现金」的策略权益曲线。"""
    return [
        EquityPoint(ts=b.ts, cash=Decimal(0), position_value=shares * b.close,
                    equity=shares * b.close)
        for b in bars
    ]


def _div(ex: tuple[int, int, int], per: str) -> DividendEvent:
    d = date(*ex)
    return DividendEvent(register_date=d, ex_date=d, pay_date=d, per_share=Decimal(per))


def test_overlay_reinvests_dividend_next_open() -> None:
    """恒持 1000 份，bar1 派 0.15/份 = 150 元，bar2 开盘买 1 手（100 份）。"""
    bars = _flat_bars(3)
    equity = _hold_curve(bars, 1000)
    res = dividend_reinvest_overlay(
        bars, [_div((2024, 1, 3), "0.15")], equity,
        initial_cash=Decimal("1000"), lot_size=100, fee=_FEE,
    )
    assert res.strategy_return == Decimal(0)  # 价格平、不含分红
    # bar1 分红到账未投计 0.15；bar2 买 100 份花 100.1、剩 49.9 → 1149.9/1000-1
    assert res.enhanced_curve[1].value == Decimal("0.15")
    assert res.enhanced_return == Decimal("0.1499")
    assert res.dividend_boost == Decimal("0.1499")
    assert res.reinvest_shares == 100
    assert res.dividend_cash_total == Decimal("150.00")


def test_overlay_compounds_on_bucket_shares() -> None:
    """第二笔分红按（策略持仓 + 分红桶）一起算，体现再投复利。"""
    bars = _flat_bars(4)
    equity = _hold_curve(bars, 1000)
    res = dividend_reinvest_overlay(
        bars, [_div((2024, 1, 3), "0.15"), _div((2024, 1, 5), "0.15")], equity,
        initial_cash=Decimal("1000"), lot_size=100, fee=_FEE,
    )
    # 第二笔在 bar3(2024-01-05)：此时分红桶已有 100 份 → 派 (1000+100)*0.15 = 165
    assert res.dividend_cash_total == Decimal("315.00")  # 150 + 165


def test_overlay_length_mismatch_raises() -> None:
    bars = _flat_bars(3)
    with pytest.raises(ValueError, match="不一致"):
        dividend_reinvest_overlay(
            bars, [], _hold_curve(bars, 100)[:2],
            initial_cash=Decimal("1000"), lot_size=100, fee=_FEE,
        )


def _series(prices: list[str]) -> BarSeries:
    bars = tuple(_bar(date(2024, 1, 2 + i), p, p) for i, p in enumerate(prices))
    return BarSeries(symbol="510880", frame=Frame.DAILY, bars=bars)


def test_dca_combo_dividend_boosts_return() -> None:
    """定投 + 分红再投：有分红时增强收益应高于纯价格口径。"""
    bars = _series(["1.00"] * 6)
    config = DcaConfig(
        symbol="510880", frequency=Frequency.DAILY,
        base_amount=Decimal("1000"), cash_cap=Decimal("10000"),
    )
    res = dca_dividend_combo(config, bars, [_div((2024, 1, 4), "0.20")])
    assert res.dividend_boost > Decimal(0)
    assert res.enhanced_return > res.strategy_return
    assert len(res.strategy_curve) == len(bars.bars)


def test_grid_combo_runs_and_structures() -> None:
    """网格 + 分红再投：跑通、结构正确，增强不低于价格口径。"""
    bars = _series(["1.00", "0.98", "1.00", "1.02", "1.00", "0.98"])
    config = GridConfig(
        symbol="510880", lower_price=Decimal("0.95"), upper_price=Decimal("1.05"),
        grid_count=10, per_grid_amount=Decimal("2000"), capital_cap=Decimal("50000"),
    )
    res = grid_dividend_combo(config, bars, [_div((2024, 1, 4), "0.05")])
    assert len(res.enhanced_curve) == len(bars.bars)
    assert res.enhanced_return >= res.strategy_return
