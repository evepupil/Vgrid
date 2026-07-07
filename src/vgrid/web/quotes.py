"""实时报价：批量取多标的现价 + 昨收 + 涨跌（FR-11.1 / 11.4）。

``QuoteProvider`` 是协议，``AkshareSpotProvider`` 是 akshare 实现——拉一次全量 ETF
现货表（``fund_etf_spot_em``）再按代码批量提取，昨收缺失则由涨跌幅反推。列名随
akshare 版本会变，适配集中在本文件；取不到的标的跳过，整体失败由调用方降级。

后端只回原始数值 + 昨收，红涨绿跌的颜色由前端定（见需求原则 4）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Quote:
    """一个标的的实时报价。"""

    symbol: str
    name: str | None
    price: Decimal
    prev_close: Decimal | None  # 昨收
    change: Decimal | None  # 涨跌额
    change_pct: Decimal | None  # 涨跌幅（%）


@runtime_checkable
class QuoteProvider(Protocol):
    """批量实时报价。"""

    def fetch_many(self, symbols: list[str]) -> list[Quote]: ...


class AkshareSpotProvider:
    """akshare ETF 全量现货表，按代码批量提取。"""

    def fetch_many(self, symbols: list[str]) -> list[Quote]:
        import akshare as ak  # noqa: PLC0415  懒导入，避免模块加载依赖网络 / akshare

        df = ak.fund_etf_spot_em()
        wanted = set(symbols)
        by_code: dict[str, Quote] = {}
        for _, row in df[df["代码"].isin(wanted)].iterrows():
            code = str(row["代码"])
            by_code[code] = _row_to_quote(code, dict(row))
        # 保持请求顺序
        return [by_code[s] for s in symbols if s in by_code]


def _row_to_quote(code: str, row: dict[str, object]) -> Quote:
    """现货表一行 → Quote，昨收 / 涨跌互相补齐。"""
    price = _dec(row.get("最新价"))
    if price is None:
        # 没有现价的行无意义，用 0 占位（调用方会拿到，但前端可判 price<=0 跳过）
        price = Decimal(0)
    prev_close = _dec(row.get("昨收"))
    change = _dec(row.get("涨跌额"))
    change_pct = _dec(row.get("涨跌幅"))
    name_raw = row.get("名称")
    name = str(name_raw) if name_raw is not None else None

    # 昨收缺 → 由涨跌幅反推
    if prev_close is None and change_pct is not None and price > 0:
        denom = Decimal(1) + change_pct / Decimal(100)
        if denom != 0:
            prev_close = price / denom
    # 涨跌额 / 涨跌幅 缺 → 由昨收补
    if prev_close is not None and prev_close != 0:
        if change is None:
            change = price - prev_close
        if change_pct is None:
            change_pct = (price - prev_close) / prev_close * Decimal(100)

    return Quote(
        symbol=code,
        name=name,
        price=price,
        prev_close=prev_close,
        change=change,
        change_pct=change_pct,
    )


def _dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def quote_to_dict(q: Quote) -> dict[str, object]:
    """Quote → JSON 安全 dict（Decimal 转 str 保精度）。"""
    return {
        "symbol": q.symbol,
        "name": q.name,
        "price": str(q.price),
        "prev_close": str(q.prev_close) if q.prev_close is not None else None,
        "change": str(q.change) if q.change is not None else None,
        "change_pct": str(q.change_pct) if q.change_pct is not None else None,
    }
