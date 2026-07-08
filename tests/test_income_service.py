"""红利对比编排测试：定池 / 逐只抓取 / 跳过无日线 / 排名（全用注入替身，不打网）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.income.models import DividendEvent, NavPoint
from vgrid.income.service import IncomeCompareSpec, build_comparison

_NAMES = {
    "510880": "上证红利ETF",
    "512890": "红利低波ETF",
    "159901": "深证100ETF",  # 非红利，关键词筛不中
}


def _bars(prices: list[str]) -> list[Bar]:
    out = []
    for i, p in enumerate(prices):
        d = date(2024, 1, 2 + i)
        px = Decimal(p)
        out.append(Bar(ts=datetime(d.year, d.month, d.day), open=px, high=px, low=px,
                       close=px, volume=Decimal("1000")))
    return out


def _div(ex: tuple[int, int, int], per: str) -> DividendEvent:
    d = date(*ex)
    return DividendEvent(register_date=d, ex_date=d, pay_date=d, per_share=Decimal(per))


def _spec(**kw: object) -> IncomeCompareSpec:
    base: dict[str, object] = {"start": date(2024, 1, 2), "end": date(2024, 1, 10)}
    base.update(kw)
    return IncomeCompareSpec(**base)  # type: ignore[arg-type]


def test_keyword_pool_and_ranking() -> None:
    # 510880 涨、512890 平；默认排序按再投年化，510880 应在前。
    bars_map = {
        "510880": _bars(["1.00", "1.10", "1.20"]),
        "512890": _bars(["1.00", "1.00", "1.00"]),
    }
    run = build_comparison(
        _spec(),
        names_fn=lambda: _NAMES,
        bars_fn=lambda code, _s, _e: bars_map[code],
        dividends_fn=lambda _c: [_div((2024, 1, 3), "0.02")],
        navs_fn=lambda _c, _s, _e: [],
    )
    # 159901 非红利被关键词筛掉，池只 2 只
    assert run.pool_size == 2
    codes = [r.code for r in run.comparison.results]
    assert codes == ["510880", "512890"]
    assert not run.skipped


def test_skips_etf_without_bars() -> None:
    run = build_comparison(
        _spec(symbols=("510880", "512890")),
        names_fn=lambda: _NAMES,
        bars_fn=lambda code, _s, _e: _bars(["1.00", "1.10"]) if code == "510880" else [],
        dividends_fn=lambda _c: [],
        navs_fn=lambda _c, _s, _e: [],
    )
    assert run.pool_size == 2
    assert [r.code for r in run.comparison.results] == ["510880"]
    assert run.skipped == ["512890"]


def test_explicit_symbols_skip_keyword_filter() -> None:
    # 显式 symbols：即便名录里 159901 不是红利，也照跑
    run = build_comparison(
        _spec(symbols=("159901",)),
        names_fn=lambda: _NAMES,
        bars_fn=lambda _c, _s, _e: _bars(["1.00", "1.05"]),
        dividends_fn=lambda _c: [],
        navs_fn=lambda _c, _s, _e: [NavPoint(date(2024, 1, 2), Decimal("1"), Decimal("2"))],
    )
    assert run.pool_size == 1
    r = run.comparison.results[0]
    assert r.code == "159901"
    assert r.name == "深证100ETF"


def test_progress_callback_fires_per_etf() -> None:
    seen: list[str] = []
    build_comparison(
        _spec(symbols=("510880", "512890")),
        names_fn=lambda: _NAMES,
        bars_fn=lambda _c, _s, _e: _bars(["1.00", "1.05"]),
        dividends_fn=lambda _c: [],
        navs_fn=lambda _c, _s, _e: [],
        on_progress=lambda _d, _t, code: seen.append(code),
    )
    assert seen == ["510880", "512890"]
