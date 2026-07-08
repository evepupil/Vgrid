"""分红明细：东财 ``fund_open_fund_info_em(分红送配详情)`` 取单只 ETF 的全历史分红。

实测这个接口给的是**全历史**每笔分红（510880 一次拿到 2007→今 19 行），而
``fund_fh_em`` 只有最近一笔——所以红利对比用前者。每份分红是「每份派现金0.1430元」
这样的字串，需解析出数字。解析是纯函数、单测覆盖；抓取是薄封装、按需注入替身。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from vgrid.income.models import DividendEvent

_INDICATOR = "分红送配详情"
# 锚定"X元"里的金额，避开"每10份"里的 10 被误当金额。
_AMOUNT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*元")
_PER_10 = "10份"  # "每10份派现金..." 需除以 10 归一到每份

# 抓取原始行的可注入函数：symbol -> [{列名: 值}]（值统一转 str）。
DividendFetch = Callable[[str], list[dict[str, str]]]


def _parse_amount(text: str) -> Decimal | None:
    """从「每份派现金0.1430元」解析每份分红；「每10份...」除以 10 归一。"""
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    try:
        amount = Decimal(m.group(1))
    except InvalidOperation:
        return None
    if _PER_10 in text:
        amount /= 10
    return amount if amount > 0 else None


def _parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def parse_dividend_rows(rows: list[dict[str, str]]) -> list[DividendEvent]:
    """把东财原始行解析成分红事件，按除息日升序。解析不了的行（缺日期 / 金额）跳过。"""
    events: list[DividendEvent] = []
    for row in rows:
        per_share = _parse_amount(row.get("每份分红", ""))
        ex = _parse_date(row.get("除息日", ""))
        register = _parse_date(row.get("权益登记日", "")) or ex
        pay = _parse_date(row.get("分红发放日", "")) or ex
        if per_share is None or ex is None or register is None or pay is None:
            continue
        # 极少数发放日早于登记日的脏数据，用除息日兜底保证不违反不变式。
        if pay < register:
            pay = ex
        events.append(
            DividendEvent(register_date=register, ex_date=ex, pay_date=pay, per_share=per_share),
        )
    events.sort(key=lambda e: e.ex_date)
    return events


def _ak_dividend_rows(symbol: str) -> list[dict[str, str]]:
    """默认抓取：东财开基分红送配详情（ETF 代码可用）。"""
    import akshare as ak  # noqa: PLC0415  懒导入，避免 income 模块加载即拉重的 akshare

    raw = ak.fund_open_fund_info_em(symbol=symbol, indicator=_INDICATOR)
    return [{str(k): str(v) for k, v in rec.items()} for rec in raw.to_dict("records")]


def fetch_dividends(
    symbol: str,
    *,
    fetch: DividendFetch = _ak_dividend_rows,
) -> list[DividendEvent]:
    """取单只 ETF 的全历史分红事件（默认走东财，测试可注入 ``fetch`` 替身）。"""
    return parse_dividend_rows(fetch(symbol))
