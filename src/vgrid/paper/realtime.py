"""实时行情 provider（模拟盘盘中轮询取现价）。

``RealtimeProvider`` 是协议；``MootdxRealtimeProvider`` 是通达信实现——走
``data.mootdx_quotes`` 的共享连接按 symbol 取现价。东财现货表（``fund_etf_spot_em``）
海外常年超时，已全面换成通达信协议（稳定不限 IP）。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from vgrid.data.mootdx_quotes import MootdxQuotes


@runtime_checkable
class RealtimeProvider(Protocol):
    """实时行情：取一个标的的当前价 + 时间戳。"""

    def fetch(self, symbol: str) -> tuple[datetime, Decimal]: ...


class MootdxRealtimeProvider:
    """通达信实时行情（按 symbol 取现价，连接复用）。"""

    def __init__(self) -> None:
        self._quotes = MootdxQuotes()

    def fetch(self, symbol: str) -> tuple[datetime, Decimal]:
        snaps = self._quotes.snapshot([symbol])
        if not snaps:
            raise ValueError(f"实时行情找不到标的：{symbol}")
        return datetime.now(), snaps[0].price
