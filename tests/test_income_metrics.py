"""收益 / 分红率 / 数据质量指标测试。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.income import series
from vgrid.income.metrics import DataQuality, compute_income_metrics
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint

_LOT = 100
_CASH = Decimal("10000")
_UNKNOWN_EXP = ExpenseInfo.unknown()


def _bars(prices: list[str], start: date = date(2024, 1, 2)) -> list[Bar]:
    out = []
    for i, p in enumerate(prices):
        d = date(start.year, start.month, start.day + i)
        px = Decimal(p)
        out.append(Bar(ts=datetime(d.year, d.month, d.day), open=px, high=px, low=px,
                       close=px, volume=Decimal("1000")))
    return out


def _div(day: tuple[int, int, int], per_share: str) -> DividendEvent:
    d = date(*day)
    return DividendEvent(register_date=d, ex_date=d, pay_date=d, per_share=Decimal(per_share))


def _compute(bars, dividends, navs, expenses=_UNKNOWN_EXP, lifetime=None):
    price_c = series.price_curve(bars)
    cash_c = series.cash_dividend_curve(bars, dividends, initial_cash=_CASH, lot_size=_LOT)
    reinvest_c = series.reinvest_curve(
        bars, dividends, initial_cash=_CASH, lot_size=_LOT, fee=series.FeeModel(),
    )
    accnav_c = series.acc_nav_curve(navs)
    return compute_income_metrics(
        bars=bars, dividends=dividends, navs=navs,
        price_c=price_c, cash_c=cash_c, reinvest_c=reinvest_c, accnav_c=accnav_c,
        expenses=expenses, initial_cash=_CASH, lot_size=_LOT, lifetime_per_share=lifetime,
    )


def test_returns_and_dividend_stats() -> None:
    bars = _bars(["1.00", "1.00", "1.00"])
    navs = [NavPoint(date(2024, 1, 2 + i), Decimal("1.0"), Decimal("2.0")) for i in range(3)]
    div = [_div((2024, 1, 3), "0.031")]
    m = _compute(bars, div, navs)

    assert m.sample_start == date(2024, 1, 2)
    assert m.sample_end == date(2024, 1, 4)
    assert m.price_return == Decimal(0)
    assert m.cash_dividend_return == Decimal("0.031")
    assert m.reinvest_return == Decimal("0.03099")
    assert m.n_dividends == 1
    assert m.sample_per_share == Decimal("0.031")
    # 期初满仓 10000 份 × 0.031 = 310 元
    assert m.sample_dividend_cash == Decimal("310.000")
    # 样本期分红率 = 0.031 / 1.00
    assert m.sample_dividend_yield == Decimal("0.031")


def test_ttm_excludes_old_dividends() -> None:
    """样本跨两年，近 12 月分红率只算末日往前 365 天内的除息。"""
    bars = _bars(["1.00"] * 3, start=date(2024, 1, 2))
    bars += _bars(["1.00"] * 3, start=date(2025, 6, 2))
    # 一笔早于 12 个月（2024-01-03），一笔在窗口内（2025-06-03）
    div = [_div((2024, 1, 3), "0.02"), _div((2025, 6, 3), "0.05")]
    m = _compute(bars, div, [])
    assert m.n_dividends == 2
    assert m.sample_per_share == Decimal("0.07")
    # 近 12 月只剩 0.05，末价 1.00
    assert m.ttm_dividend_yield == Decimal("0.05")


def test_data_quality_price_only() -> None:
    m = _compute(_bars(["1.00", "1.00"]), [], [])
    assert m.data_quality is DataQuality.PRICE_ONLY
    assert m.acc_nav_return is None


def test_data_quality_missing_nav() -> None:
    m = _compute(_bars(["1.00", "1.00"]), [_div((2024, 1, 3), "0.01")], [])
    assert m.data_quality is DataQuality.MISSING_NAV


def test_data_quality_missing_dividend() -> None:
    navs = [NavPoint(date(2024, 1, 2 + i), Decimal("1.0"), Decimal("2.0")) for i in range(2)]
    m = _compute(_bars(["1.00", "1.00"]), [], navs)
    assert m.data_quality is DataQuality.MISSING_DIVIDEND


def test_data_quality_ok_when_aligned() -> None:
    bars = _bars(["1.00", "1.00", "1.00"])
    navs = [NavPoint(date(2024, 1, 2 + i), Decimal("1.0"), Decimal("2.0")) for i in range(3)]
    div = [_div((2024, 1, 3), "0.031")]
    m = _compute(bars, div, navs)
    assert m.data_quality is DataQuality.OK
    assert m.warnings == ()


def test_data_quality_partial_on_divergence() -> None:
    """再投几乎不涨(价格平)，而累计净值翻倍 → 差异过大，判 partial 带警告。"""
    bars = _bars(["1.00", "1.00", "1.00"])
    navs = [
        NavPoint(date(2024, 1, 2), Decimal("1.0"), Decimal("2.0")),
        NavPoint(date(2024, 1, 3), Decimal("1.0"), Decimal("3.0")),
        NavPoint(date(2024, 1, 4), Decimal("1.0"), Decimal("4.0")),  # +100%
    ]
    div = [_div((2024, 1, 3), "0.031")]
    m = _compute(bars, div, navs)
    assert m.data_quality is DataQuality.PARTIAL
    assert any("口径可能不一致" in w for w in m.warnings)


def test_expense_passthrough() -> None:
    exp = ExpenseInfo(
        management_rate=Decimal("0.005"), custody_rate=Decimal("0.001"),
        sales_rate=None, total_rate=Decimal("0.006"), source="test", updated="2026-07-08",
    )
    m = _compute(_bars(["1.00", "1.00"]), [], [], expenses=exp)
    assert m.total_expense_rate == Decimal("0.006")
