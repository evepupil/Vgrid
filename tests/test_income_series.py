"""四条收益曲线测试：价格 / 现金分红 / 分红再投（无未来函数、扣费、取整）/ 累计净值。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from vgrid.core.bar import Bar
from vgrid.core.fees import FeeModel
from vgrid.income.models import DividendEvent, NavPoint
from vgrid.income.series import (
    acc_nav_curve,
    cash_dividend_curve,
    price_curve,
    reinvest_curve,
)

_LOT = 100
_CASH = Decimal("10000")
_FEE = FeeModel()


def _bar(day: date, open_: str, close: str) -> Bar:
    o, c = Decimal(open_), Decimal(close)
    return Bar(
        ts=datetime(day.year, day.month, day.day),
        open=o,
        high=max(o, c),
        low=min(o, c),
        close=c,
        volume=Decimal("1000"),
    )


def _flat_bars(prices: list[str]) -> list[Bar]:
    """open=close=价格 的日线（2024-01-02 起逐日）。"""
    return [_bar(date(2024, 1, 2 + i), p, p) for i, p in enumerate(prices)]


def _div(day: tuple[int, int, int], per_share: str) -> DividendEvent:
    d = date(*day)
    return DividendEvent(register_date=d, ex_date=d, pay_date=d, per_share=Decimal(per_share))


def test_price_curve_relative_to_first() -> None:
    bars = _flat_bars(["1.00", "1.10", "1.20"])
    vals = [p.value for p in price_curve(bars)]
    assert vals == [Decimal(0), Decimal("0.1"), Decimal("0.2")]


def test_acc_nav_curve_relative_to_first() -> None:
    navs = [
        NavPoint(date(2024, 1, 2), Decimal("1.0"), Decimal("2.0")),
        NavPoint(date(2024, 1, 3), Decimal("1.0"), Decimal("2.2")),
        NavPoint(date(2024, 1, 4), Decimal("1.0"), Decimal("2.4")),
    ]
    vals = [p.value for p in acc_nav_curve(navs)]
    assert vals == [Decimal(0), Decimal("0.1"), Decimal("0.2")]


def test_empty_inputs_return_empty() -> None:
    assert price_curve([]) == []
    assert acc_nav_curve([]) == []
    assert cash_dividend_curve([], [], initial_cash=_CASH, lot_size=_LOT) == []
    assert reinvest_curve([], [], initial_cash=_CASH, lot_size=_LOT, fee=_FEE) == []


def test_cash_dividend_no_dividend_matches_price() -> None:
    """无分红 + 首日满仓（现金 0），现金分红曲线应与价格曲线一致。"""
    bars = _flat_bars(["1.00", "1.00", "2.00"])
    cash = [p.value for p in cash_dividend_curve(bars, [], initial_cash=_CASH, lot_size=_LOT)]
    price = [p.value for p in price_curve(bars)]
    assert cash == price == [Decimal(0), Decimal(0), Decimal(1)]


def test_cash_dividend_adds_cash_on_pay_bar() -> None:
    """每份 0.031 × 10000 份 = 310 元现金，发放日那根起并入权益。"""
    bars = _flat_bars(["1.00", "1.00", "1.00"])
    div = [_div((2024, 1, 3), "0.031")]  # 落在 index=1
    vals = [p.value for p in cash_dividend_curve(bars, div, initial_cash=_CASH, lot_size=_LOT)]
    assert vals == [Decimal(0), Decimal("0.031"), Decimal("0.031")]


def test_dividend_outside_sample_ignored() -> None:
    """发放日晚于末根 bar 的分红不计入。"""
    bars = _flat_bars(["1.00", "1.00", "1.00"])
    div = [_div((2024, 2, 1), "0.031")]  # 晚于 2024-01-04
    vals = [p.value for p in cash_dividend_curve(bars, div, initial_cash=_CASH, lot_size=_LOT)]
    assert vals == [Decimal(0), Decimal(0), Decimal(0)]


def test_reinvest_no_lookahead_and_fee() -> None:
    """发放日(bar1)收现金记为现金，下一根(bar2)开盘才买入，扣一次费。"""
    bars = _flat_bars(["1.00", "1.00", "1.00"])
    div = [_div((2024, 1, 3), "0.031")]  # 310 元
    pts = reinvest_curve(bars, div, initial_cash=_CASH, lot_size=_LOT, fee=_FEE)
    vals = [p.value for p in pts]
    # bar1：310 元还没投，作现金计入 → 0.031
    assert vals[0] == Decimal(0)
    assert vals[1] == Decimal("0.031")
    # bar2：310 元买 300 份（3 手），花 300 + 0.1 费，剩 9.9 现金
    # 权益 = 10300×1.00 + 9.9 = 10309.9 → 0.03099
    assert vals[2] == Decimal("0.03099")


def test_reinvest_beats_cash_when_price_rises() -> None:
    """价格在分红后上涨时，再投的份额增值超过纯留现金。"""
    bars = [
        _bar(date(2024, 1, 2), "1.00", "1.00"),
        _bar(date(2024, 1, 3), "1.00", "1.00"),  # 发放日
        _bar(date(2024, 1, 4), "1.00", "1.10"),  # 开盘 1.00 买入、收盘 1.10
    ]
    div = [_div((2024, 1, 3), "0.031")]
    reinvest = reinvest_curve(bars, div, initial_cash=_CASH, lot_size=_LOT, fee=_FEE)
    cash = cash_dividend_curve(bars, div, initial_cash=_CASH, lot_size=_LOT)
    # 再投 bar2：10300×1.10 + 9.9 = 11339.9 → 0.13399
    assert reinvest[2].value == Decimal("0.13399")
    # 现金 bar2：10000×1.10 + 310 = 11310 → 0.131
    assert cash[2].value == Decimal("0.131")
    assert reinvest[2].value > cash[2].value


def test_initial_cash_too_small_raises() -> None:
    bars = _flat_bars(["1.00", "1.00"])
    with pytest.raises(ValueError, match="买不满一手"):
        cash_dividend_curve(bars, [], initial_cash=Decimal("50"), lot_size=_LOT)
