"""红利 ETF 收益对比的结果模型与排名（纯逻辑）。

``build_etf_result`` 把单只 ETF 的原始输入（日线 / 分红 / 净值 / 费用）算成四条曲线 +
一套指标，打包成 ``EtfIncomeResult``；``rank_etfs`` 按可配排序键给一批结果排横向名次。
渲染成 Markdown / CSV 的活儿在 ``report/income.py``，这里只出结构化结果。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.core.fees import FeeModel
from vgrid.income import series
from vgrid.income.metrics import IncomeMetrics, compute_income_metrics
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint
from vgrid.income.series import SeriesPoint


@dataclass(frozen=True, slots=True)
class EtfIncomeResult:
    """单只红利 ETF 的完整对比结果：身份 + 四曲线 + 指标 + 分红明细 + 费用。"""

    code: str
    name: str
    inception: date | None
    metrics: IncomeMetrics
    price_curve: list[SeriesPoint]
    cash_dividend_curve: list[SeriesPoint]
    reinvest_curve: list[SeriesPoint]
    acc_nav_curve: list[SeriesPoint]
    dividends: list[DividendEvent]  # 样本期内的分红事件（供报告展开明细）
    expenses: ExpenseInfo


@dataclass(frozen=True, slots=True)
class IncomeComparison:
    """一批红利 ETF 的横向对比（已按 ``sort_keys`` 排好名次）。"""

    results: list[EtfIncomeResult]
    sort_keys: tuple[str, ...]


def build_etf_result(
    *,
    code: str,
    name: str,
    bars: list[Bar],
    dividends: list[DividendEvent],
    navs: list[NavPoint],
    expenses: ExpenseInfo,
    initial_cash: Decimal,
    lot_size: int,
    fee: FeeModel,
    inception: date | None = None,
    lifetime_per_share: Decimal | None = None,
) -> EtfIncomeResult:
    """把单只 ETF 的原始输入算成四条曲线 + 指标，打包成结果。"""
    if not bars:
        raise ValueError(f"{code} 无日线数据，无法生成对比结果")

    price_c = series.price_curve(bars)
    cash_c = series.cash_dividend_curve(
        bars, dividends, initial_cash=initial_cash, lot_size=lot_size,
    )
    reinvest_c = series.reinvest_curve(
        bars, dividends, initial_cash=initial_cash, lot_size=lot_size, fee=fee,
    )
    accnav_c = series.acc_nav_curve(navs)

    metrics = compute_income_metrics(
        bars=bars,
        dividends=dividends,
        navs=navs,
        price_c=price_c,
        cash_c=cash_c,
        reinvest_c=reinvest_c,
        accnav_c=accnav_c,
        expenses=expenses,
        initial_cash=initial_cash,
        lot_size=lot_size,
        lifetime_per_share=lifetime_per_share,
    )

    start, end = bars[0].ts.date(), bars[-1].ts.date()
    in_sample = [ev for ev in dividends if start <= ev.ex_date <= end]
    return EtfIncomeResult(
        code=code,
        name=name,
        inception=inception,
        metrics=metrics,
        price_curve=price_c,
        cash_dividend_curve=cash_c,
        reinvest_curve=reinvest_c,
        acc_nav_curve=accnav_c,
        dividends=in_sample,
        expenses=expenses,
    )


# 排序键 → (取值, 是否降序)。费用未知按大值排后（升序时垫底）。
_BIG = Decimal(10) ** 9
_SortSpec = tuple[Callable[[EtfIncomeResult], Decimal], bool]
_SORT_SPECS: dict[str, _SortSpec] = {
    "annualized": (lambda r: r.metrics.annualized_return, True),
    "reinvest": (lambda r: r.metrics.reinvest_return, True),
    "price": (lambda r: r.metrics.price_return, True),
    "drawdown": (lambda r: r.metrics.max_drawdown, False),
    "ttm_yield": (lambda r: r.metrics.ttm_dividend_yield, True),
    "sample_yield": (lambda r: r.metrics.sample_dividend_yield, True),
    "expense": (lambda r: r.metrics.total_expense_rate or _BIG, False),
}

# 默认横向排名：再投年化高 → 回撤低 → 近 12 月分红率高 → 费用低。
DEFAULT_SORT: tuple[str, ...] = ("annualized", "drawdown", "ttm_yield", "expense")


def rank_etfs(
    results: Sequence[EtfIncomeResult],
    sort_keys: Sequence[str] = DEFAULT_SORT,
) -> IncomeComparison:
    """按排序键给一批结果排名。多键按先后主次，靠从次到主的稳定排序实现。"""
    keys = tuple(sort_keys)
    for key in keys:
        if key not in _SORT_SPECS:
            raise ValueError(f"未知排序键：{key}（可选 {sorted(_SORT_SPECS)}）")

    ranked = list(results)
    for key in reversed(keys):
        accessor, reverse = _SORT_SPECS[key]
        ranked.sort(key=accessor, reverse=reverse)
    return IncomeComparison(results=ranked, sort_keys=keys)
