"""红利 ETF 对比编排：定池 → 逐只抓行情 / 分红 / 净值 / 费用 → 算结果 → 排名。

所有 I/O 端口（名录 / 不复权日线 / 分红 / 净值 / 费用）都可注入，默认接生产源
（mootdx 名录 + 腾讯不复权日线 + 东财分红净值），测试传替身即可离线跑通整条链。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.core.enums import Frame
from vgrid.core.fees import FeeModel
from vgrid.data.loader import load_bars
from vgrid.income.dividends import fetch_dividends
from vgrid.income.expenses import fetch_expenses
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint
from vgrid.income.nav import fetch_navs
from vgrid.income.report import DEFAULT_SORT, IncomeComparison, build_etf_result, rank_etfs
from vgrid.income.universe import DEFAULT_KEYWORDS, EtfRef, filter_dividend_etfs

# 可注入端口。
NameSource = Callable[[], dict[str, str]]
BarSource = Callable[[str, date, date], list[Bar]]
DividendSource = Callable[[str], list[DividendEvent]]
NavSource = Callable[[str, date, date], list[NavPoint]]
ExpenseSource = Callable[[str], ExpenseInfo]
Progress = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class IncomeCompareSpec:
    """一次红利对比的入参。``symbols`` 给了就跳过关键词筛选。"""

    start: date
    end: date
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS
    symbols: tuple[str, ...] = ()
    initial_cash: Decimal = Decimal("100000")
    lot_size: int = 100
    fee: FeeModel = field(default_factory=FeeModel)
    sort_keys: tuple[str, ...] = DEFAULT_SORT


@dataclass(frozen=True, slots=True)
class IncomeCompareRun:
    """一次对比的完整产出：排名结果 + 池规模 + 因无日线被跳过的代码。"""

    comparison: IncomeComparison
    pool_size: int
    skipped: list[str]
    spec: IncomeCompareSpec


def _default_names() -> dict[str, str]:
    from vgrid.data.mootdx_quotes import MootdxQuotes  # noqa: PLC0415  懒导入，避免连 mootdx

    return MootdxQuotes().names()


def _default_bars(code: str, start: date, end: date) -> list[Bar]:
    # 红利收益对比要**不复权**价（手动叠分红），故 adjust=""。
    return list(load_bars(code, start, end, Frame.DAILY, adjust="").bars)


def _resolve_pool(spec: IncomeCompareSpec, names_fn: NameSource) -> list[EtfRef]:
    """定池：显式 symbols 优先（名录取名、缺名回落代码），否则按关键词筛。"""
    if spec.symbols:
        names = names_fn()
        return [EtfRef(code=s, name=names.get(s, s)) for s in spec.symbols]
    return filter_dividend_etfs(names_fn(), spec.keywords)


def build_comparison(
    spec: IncomeCompareSpec,
    *,
    names_fn: NameSource = _default_names,
    bars_fn: BarSource = _default_bars,
    dividends_fn: DividendSource = fetch_dividends,
    navs_fn: NavSource = fetch_navs,
    expenses_fn: ExpenseSource = fetch_expenses,
    on_progress: Progress | None = None,
) -> IncomeCompareRun:
    """跑一次红利对比。无日线的 ETF 记入 skipped、不进排名。"""
    pool = _resolve_pool(spec, names_fn)
    results = []
    skipped: list[str] = []
    for i, ref in enumerate(pool):
        if on_progress is not None:
            on_progress(i + 1, len(pool), ref.code)
        bars = bars_fn(ref.code, spec.start, spec.end)
        if not bars:
            skipped.append(ref.code)
            continue
        results.append(
            build_etf_result(
                code=ref.code,
                name=ref.name,
                bars=bars,
                dividends=dividends_fn(ref.code),
                navs=navs_fn(ref.code, spec.start, spec.end),
                expenses=expenses_fn(ref.code),
                initial_cash=spec.initial_cash,
                lot_size=spec.lot_size,
                fee=spec.fee,
            ),
        )
    comparison = rank_etfs(results, spec.sort_keys)
    return IncomeCompareRun(
        comparison=comparison,
        pool_size=len(pool),
        skipped=skipped,
        spec=spec,
    )
