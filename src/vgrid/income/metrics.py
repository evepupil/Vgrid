"""单只红利 ETF 的收益 / 回撤 / 分红率 / 数据质量指标（纯函数）。

四条曲线的收益率取各自末点；年化 / 回撤以「分红再投」为准（横向排名的主口径）。
分红次数 / 每份分红 / 分红率按**除息日落在样本期内**的事件算（享分红的口径），
与曲线里现金按发放日到账是两回事，分开处理。费用只展示、不从收益里扣。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from vgrid.backtest.metrics import annualized_return
from vgrid.core.bar import Bar
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint
from vgrid.income.series import SeriesPoint

_TTM_DAYS = 365
# 累计净值日期要覆盖样本期这么大比例才算完整，否则打 partial。
_NAV_COVERAGE_MIN = Decimal("0.8")
# 「分红再投」和「累计净值」末点收益差超这个阈值，判口径可能不一致。
_DIVERGENCE_WARN = Decimal("0.15")


class DataQuality(StrEnum):
    """报告里的数据完整性状态。"""

    OK = "ok"  # 数据完整
    PARTIAL = "partial"  # 有缺口但还能比较
    MISSING_DIVIDEND = "missing_dividend"  # 缺分红明细
    MISSING_NAV = "missing_nav"  # 缺净值
    PRICE_ONLY = "price_only"  # 只有价格走势


@dataclass(frozen=True, slots=True)
class IncomeMetrics:
    """单只红利 ETF 的收益对比指标。"""

    sample_start: date
    sample_end: date
    price_return: Decimal
    cash_dividend_return: Decimal
    reinvest_return: Decimal
    acc_nav_return: Decimal | None
    annualized_return: Decimal  # 分红再投口径的自然日年化
    max_drawdown: Decimal  # 分红再投口径的最大回撤
    n_dividends: int  # 样本期分红次数（按除息日）
    sample_per_share: Decimal  # 样本期每份分红之和
    lifetime_per_share: Decimal | None  # 历史累计每份分红（来自累计分红排行，可缺）
    sample_dividend_cash: Decimal  # 样本期分红金额（期初满仓份额 × 样本期每份分红）
    sample_dividend_yield: Decimal  # 样本期分红率 = 样本期每份分红 / 期初价格
    ttm_dividend_yield: Decimal  # 近 12 个月分红率 = 近 12 月每份分红 / 期末价格
    total_expense_rate: Decimal | None  # 费用合计年费率（可缺）
    data_quality: DataQuality
    warnings: tuple[str, ...]


def _last_value(curve: list[SeriesPoint]) -> Decimal:
    return curve[-1].value if curve else Decimal(0)


def _max_drawdown_of_returns(curve: list[SeriesPoint]) -> Decimal:
    """从「累计收益率」序列算最大回撤（把 1+收益 当权益）。"""
    if not curve:
        return Decimal(0)
    peak = Decimal(1) + curve[0].value
    max_dd = Decimal(0)
    for p in curve:
        equity = Decimal(1) + p.value
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd


def data_quality(
    *,
    bars: list[Bar],
    dividends_in_sample: list[DividendEvent],
    navs: list[NavPoint],
    reinvest_return: Decimal,
    acc_nav_return: Decimal | None,
) -> tuple[DataQuality, tuple[str, ...]]:
    """按分红 / 净值的有无、净值覆盖度、再投与累计净值的差异定数据质量。"""
    has_div = bool(dividends_in_sample)
    has_nav = bool(navs)
    if not has_div and not has_nav:
        return DataQuality.PRICE_ONLY, ()
    if not has_div:
        return DataQuality.MISSING_DIVIDEND, ()
    if not has_nav:
        return DataQuality.MISSING_NAV, ()

    warnings: list[str] = []
    sample_span = (bars[-1].ts.date() - bars[0].ts.date()).days
    nav_span = (navs[-1].day - navs[0].day).days
    if sample_span > 0 and Decimal(nav_span) < Decimal(sample_span) * _NAV_COVERAGE_MIN:
        warnings.append("累计净值日期未覆盖样本期大部分区间")
    if acc_nav_return is not None and abs(reinvest_return - acc_nav_return) > _DIVERGENCE_WARN:
        warnings.append(
            f"分红再投({reinvest_return:.1%})与累计净值({acc_nav_return:.1%})差异过大，"
            "数据口径可能不一致",
        )
    quality = DataQuality.PARTIAL if warnings else DataQuality.OK
    return quality, tuple(warnings)


def compute_income_metrics(
    *,
    bars: list[Bar],
    dividends: list[DividendEvent],
    navs: list[NavPoint],
    price_c: list[SeriesPoint],
    cash_c: list[SeriesPoint],
    reinvest_c: list[SeriesPoint],
    accnav_c: list[SeriesPoint],
    expenses: ExpenseInfo,
    initial_cash: Decimal,
    lot_size: int,
    lifetime_per_share: Decimal | None = None,
) -> IncomeMetrics:
    """汇总单只 ETF 的全部指标。曲线由调用方（report.build_etf_result）先算好传入。"""
    if not bars:
        raise ValueError("无日线数据，无法计算指标")

    start = bars[0].ts.date()
    end = bars[-1].ts.date()
    first_close = bars[0].close
    last_close = bars[-1].close

    in_sample = [ev for ev in dividends if start <= ev.ex_date <= end]
    sample_per_share = sum((ev.per_share for ev in in_sample), Decimal(0))
    shares0 = int((initial_cash / first_close) // lot_size) * lot_size

    ttm_cutoff = end - timedelta(days=_TTM_DAYS)
    ttm_per_share = sum(
        (ev.per_share for ev in in_sample if ev.ex_date > ttm_cutoff),
        Decimal(0),
    )

    reinvest_return = _last_value(reinvest_c)
    acc_nav_return = _last_value(accnav_c) if navs else None
    quality, warnings = data_quality(
        bars=bars,
        dividends_in_sample=in_sample,
        navs=navs,
        reinvest_return=reinvest_return,
        acc_nav_return=acc_nav_return,
    )

    return IncomeMetrics(
        sample_start=start,
        sample_end=end,
        price_return=_last_value(price_c),
        cash_dividend_return=_last_value(cash_c),
        reinvest_return=reinvest_return,
        acc_nav_return=acc_nav_return,
        annualized_return=annualized_return(reinvest_return, tuple(bars)),
        max_drawdown=_max_drawdown_of_returns(reinvest_c),
        n_dividends=len(in_sample),
        sample_per_share=sample_per_share,
        lifetime_per_share=lifetime_per_share,
        sample_dividend_cash=shares0 * sample_per_share,
        sample_dividend_yield=sample_per_share / first_close,
        ttm_dividend_yield=ttm_per_share / last_close,
        total_expense_rate=expenses.total_rate,
        data_quality=quality,
        warnings=warnings,
    )
