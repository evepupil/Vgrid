"""净值走势：东财 ``fund_etf_fund_info_em`` 取单只场内基金的单位 / 累计净值。

累计净值是「含历史分红」的长期表现基准，用来校验分红再投曲线。解析纯函数、单测覆盖；
抓取薄封装、可注入替身。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from vgrid.income.models import NavPoint

# 抓取原始行的可注入函数：(symbol, start, end) -> [{列名: 值}]。
NavFetch = Callable[[str, date, date], list[dict[str, str]]]


def _dec(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip())
    except (InvalidOperation, AttributeError):
        return None
    return value if value > 0 else None


def parse_nav_rows(rows: list[dict[str, str]]) -> list[NavPoint]:
    """把东财净值行解析成 NavPoint，按日期升序。缺日期 / 净值非正的行跳过。"""
    points: list[NavPoint] = []
    for row in rows:
        try:
            day = date.fromisoformat(row.get("净值日期", "").strip())
        except ValueError:
            continue
        unit = _dec(row.get("单位净值", ""))
        acc = _dec(row.get("累计净值", ""))
        if unit is None or acc is None:
            continue
        points.append(NavPoint(day=day, unit_nav=unit, acc_nav=acc))
    points.sort(key=lambda p: p.day)
    return points


def _ak_nav_rows(symbol: str, start: date, end: date) -> list[dict[str, str]]:
    """默认抓取：东财场内基金净值。"""
    import akshare as ak  # noqa: PLC0415  懒导入，避免 income 模块加载即拉重的 akshare

    raw = ak.fund_etf_fund_info_em(
        fund=symbol,
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
    )
    return [{str(k): str(v) for k, v in rec.items()} for rec in raw.to_dict("records")]


def fetch_navs(
    symbol: str,
    start: date,
    end: date,
    *,
    fetch: NavFetch = _ak_nav_rows,
) -> list[NavPoint]:
    """取单只 ETF 在 [start, end] 的净值序列（默认走东财，测试可注入替身）。"""
    return parse_nav_rows(fetch(symbol, start, end))
