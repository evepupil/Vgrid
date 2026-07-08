"""红利 ETF 对比 API 逻辑：``build_comparison`` → JSON 安全 dict。

排名 rows 每条带 metrics + 四曲线（降采样到 ``_CURVE_POINTS``，批量 ETF × 4 曲线省带宽）。
复用 :func:`vgrid.web.curve.downsample`（泛型，对 SeriesPoint 直接用）。
"""

from __future__ import annotations

from vgrid.income.report import EtfIncomeResult
from vgrid.income.series import SeriesPoint
from vgrid.income.service import IncomeCompareRun, IncomeCompareSpec, build_comparison
from vgrid.web.curve import downsample

_CURVE_POINTS = 100  # 批量 ETF × 4 曲线，降采样狠点省带宽


def run_income_compare(spec: IncomeCompareSpec) -> dict[str, object]:
    """跑红利对比，返 JSON dict（池规模 + 跳过 + 排序键 + rows[metrics + 四曲线]）。"""
    return _run_to_dict(build_comparison(spec))


def _run_to_dict(run: IncomeCompareRun) -> dict[str, object]:
    return {
        "pool_size": run.pool_size,
        "skipped": list(run.skipped),
        "sort_keys": list(run.comparison.sort_keys),
        "initial_cash": str(run.spec.initial_cash),
        "start": run.spec.start.isoformat(),
        "end": run.spec.end.isoformat(),
        "rows": [_row_to_dict(r) for r in run.comparison.results],
    }


def _row_to_dict(r: EtfIncomeResult) -> dict[str, object]:
    m = r.metrics
    return {
        "code": r.code,
        "name": r.name,
        "inception": r.inception.isoformat() if r.inception is not None else None,
        "metrics": {
            "sample_start": m.sample_start.isoformat(),
            "sample_end": m.sample_end.isoformat(),
            "price_return": str(m.price_return),
            "cash_dividend_return": str(m.cash_dividend_return),
            "reinvest_return": str(m.reinvest_return),
            "acc_nav_return": str(m.acc_nav_return) if m.acc_nav_return is not None else None,
            "annualized_return": str(m.annualized_return),
            "max_drawdown": str(m.max_drawdown),
            "n_dividends": m.n_dividends,
            "sample_per_share": str(m.sample_per_share),
            "sample_dividend_yield": str(m.sample_dividend_yield),
            "ttm_dividend_yield": str(m.ttm_dividend_yield),
            "total_expense_rate": str(m.total_expense_rate)
            if m.total_expense_rate is not None
            else None,
            "data_quality": m.data_quality.value,
            "warnings": list(m.warnings),
        },
        "curves": {
            "price": _curve(r.price_curve),
            "cash_dividend": _curve(r.cash_dividend_curve),
            "reinvest": _curve(r.reinvest_curve),
            "acc_nav": _curve(r.acc_nav_curve),
        },
    }


def _curve(points: list[SeriesPoint]) -> list[dict[str, object]]:
    """降采样到 ``_CURVE_POINTS``，转 ``{day, value}``（value 是累计收益率，起点=0）。"""
    sampled, _ = downsample(points, _CURVE_POINTS)
    return [{"day": p.day.isoformat(), "value": str(p.value)} for p in sampled]
