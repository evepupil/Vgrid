"""mootdx 实时报价 + 证券名称（通达信协议，替代东财 ``fund_etf_spot_em``）。

``quotes()`` 一次批量取多标的的现价 / 昨收 / 开高低；``stocks()`` 出全市场证券列表
（代码→名称）。都走 ``data.mootdx_client`` 的共享连接。返回原始数值，红涨绿跌颜色由前端定。

东财现货表（``fund_etf_spot_em``）海外常年超时，通达信协议稳定不限 IP，这里全面换成它。
名称一项要拉全市场列表（沪 + 深各几千只，翻页），比只拉 ETF 现货表重，调用方自己缓存。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from vgrid.data.mootdx_client import MootdxConnection

# 沪深市场编码（mootdx：0=深，1=沪）；ETF 5 开头在沪、1 开头在深
_MARKETS = (0, 1)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """一个标的的实时快照（通达信 ``quotes`` 一行）。"""

    code: str
    price: Decimal
    last_close: Decimal | None  # 昨收
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None


class MootdxQuotes:
    """通达信实时报价 + 名称，连接复用（首次调用建连、异常重连一次）。"""

    def __init__(self) -> None:
        self._conn = MootdxConnection()

    def snapshot(self, symbols: list[str]) -> list[Snapshot]:
        """批量取现价 / 昨收，按请求顺序返回；取不到的标的跳过。"""
        if not symbols:
            return []
        df = self._conn.quotes(list(symbols))
        if df is None or len(df) == 0:
            return []
        by_code: dict[str, Snapshot] = {}
        for row in df.to_dict("records"):
            code = str(row.get("code", "")).zfill(6)
            by_code[code] = _row_to_snapshot(code, row)
        return [by_code[s] for s in symbols if s in by_code]

    def names(self) -> dict[str, str]:
        """全市场 代码→名称（沪 + 深）。首次拉取较慢，调用方负责缓存。"""
        out: dict[str, str] = {}
        for market in _MARKETS:
            df = self._conn.stocks(market)
            if df is None or len(df) == 0:
                continue
            for row in df.to_dict("records"):
                code = str(row.get("code", "")).zfill(6)
                name = _clean_name(str(row.get("name", "")))
                if code and name:
                    out[code] = name
        return out


def _clean_name(raw: str) -> str:
    """清掉名称里的控制字符（mootdx 部分标的名带尾部 \\x00，字体渲染成缺字方块）后 strip。"""
    return "".join(ch for ch in raw if ch >= " ").strip()


def _row_to_snapshot(code: str, row: dict[str, object]) -> Snapshot:
    price = _dec(row.get("price")) or Decimal(0)
    last_close = _dec(row.get("last_close"))
    # 昨收为 0（部分标的停牌 / 数据缺）当作没有，别让下游算出 ±100% 的假涨跌
    if last_close is not None and last_close <= 0:
        last_close = None
    return Snapshot(
        code=code,
        price=price,
        last_close=last_close,
        open=_dec(row.get("open")),
        high=_dec(row.get("high")),
        low=_dec(row.get("low")),
    )


def _dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None
