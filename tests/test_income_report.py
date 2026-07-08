"""结果编排 + 横向排名测试。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from vgrid.core.bar import Bar
from vgrid.core.fees import FeeModel
from vgrid.income.metrics import DataQuality, IncomeMetrics
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint
from vgrid.income.report import DEFAULT_SORT, EtfIncomeResult, build_etf_result, rank_etfs


def _bars(prices: list[str]) -> list[Bar]:
    out = []
    for i, p in enumerate(prices):
        d = date(2024, 1, 2 + i)
        px = Decimal(p)
        out.append(Bar(ts=datetime(d.year, d.month, d.day), open=px, high=px, low=px,
                       close=px, volume=Decimal("1000")))
    return out


def test_build_etf_result_bundles_curves_and_filters_dividends() -> None:
    bars = _bars(["1.00", "1.00", "1.00"])
    navs = [NavPoint(date(2024, 1, 2 + i), Decimal("1.0"), Decimal("2.0")) for i in range(3)]
    div_in = DividendEvent(date(2024, 1, 3), date(2024, 1, 3), date(2024, 1, 3), Decimal("0.03"))
    div_out = DividendEvent(date(2024, 2, 1), date(2024, 2, 1), date(2024, 2, 1), Decimal("0.03"))
    res = build_etf_result(
        code="510880", name="红利ETF", bars=bars, dividends=[div_in, div_out], navs=navs,
        expenses=ExpenseInfo.unknown(), initial_cash=Decimal("10000"), lot_size=100,
        fee=FeeModel(), inception=date(2007, 1, 1),
    )
    assert res.code == "510880"
    assert res.inception == date(2007, 1, 1)
    assert len(res.price_curve) == 3
    assert len(res.reinvest_curve) == 3
    assert len(res.acc_nav_curve) == 3
    # 样本外(2024-02-01)那笔被过滤掉
    assert res.dividends == [div_in]
    assert res.metrics.n_dividends == 1


def _metrics(*, annualized: str, drawdown: str, ttm: str,
             expense: str | None) -> IncomeMetrics:
    return IncomeMetrics(
        sample_start=date(2024, 1, 1), sample_end=date(2024, 12, 31),
        price_return=Decimal("0.1"), cash_dividend_return=Decimal("0.1"),
        reinvest_return=Decimal(annualized), acc_nav_return=None,
        annualized_return=Decimal(annualized), max_drawdown=Decimal(drawdown),
        n_dividends=1, sample_per_share=Decimal("0.1"), lifetime_per_share=None,
        sample_dividend_cash=Decimal("100"), sample_dividend_yield=Decimal("0.03"),
        ttm_dividend_yield=Decimal(ttm),
        total_expense_rate=Decimal(expense) if expense is not None else None,
        data_quality=DataQuality.OK, warnings=(),
    )


def _result(code: str, **kw: str | None) -> EtfIncomeResult:
    return EtfIncomeResult(
        code=code, name=code, inception=None, metrics=_metrics(**kw),  # type: ignore[arg-type]
        price_curve=[], cash_dividend_curve=[], reinvest_curve=[], acc_nav_curve=[],
        dividends=[], expenses=ExpenseInfo.unknown(),
    )


def test_rank_default_by_annualized_desc() -> None:
    a = _result("A", annualized="0.05", drawdown="0.1", ttm="0.03", expense="0.005")
    b = _result("B", annualized="0.20", drawdown="0.1", ttm="0.03", expense="0.005")
    c = _result("C", annualized="0.12", drawdown="0.1", ttm="0.03", expense="0.005")
    ranked = rank_etfs([a, b, c])
    assert [r.code for r in ranked.results] == ["B", "C", "A"]
    assert ranked.sort_keys == DEFAULT_SORT


def test_rank_tiebreak_by_lower_drawdown() -> None:
    """年化相同 → 回撤低的在前。"""
    a = _result("A", annualized="0.10", drawdown="0.30", ttm="0.03", expense="0.005")
    b = _result("B", annualized="0.10", drawdown="0.05", ttm="0.03", expense="0.005")
    ranked = rank_etfs([a, b])
    assert [r.code for r in ranked.results] == ["B", "A"]


def test_rank_unknown_expense_sorts_last() -> None:
    """按费用升序排，费用未知(None)垫底。"""
    a = _result("A", annualized="0.10", drawdown="0.10", ttm="0.03", expense=None)
    b = _result("B", annualized="0.10", drawdown="0.10", ttm="0.03", expense="0.006")
    ranked = rank_etfs([a, b], sort_keys=["expense"])
    assert [r.code for r in ranked.results] == ["B", "A"]


def test_rank_rejects_unknown_key() -> None:
    a = _result("A", annualized="0.10", drawdown="0.10", ttm="0.03", expense="0.005")
    with pytest.raises(ValueError, match="未知排序键"):
        rank_etfs([a], sort_keys=["bogus"])
