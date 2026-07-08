"""mootdx 连接管理：建连（选最快服务器）+ 复用 + 异常重连一次。

K 线（``bars``）、实时报价（``quotes``）、证券列表（``stocks``）都走通达信同一条 TCP
连接。连接管理集中在这里，几处共用，别各写各的。模块加载不连接，首次真正调用才连；
调用中协议 / 连接异常先断开重连一次，再失败才抛。三个方法都返回 pandas DataFrame（或
无数据时 None）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import pandas as pd
from mootdx.quotes import Quotes


class MootdxClient(Protocol):
    """mootdx ``Quotes.factory`` 返回的客户端接口（只声明用到的方法）。"""

    def bars(
        self, *, symbol: str, frequency: int, offset: int, start: int
    ) -> pd.DataFrame | None: ...
    def quotes(self, *, symbol: list[str]) -> pd.DataFrame | None: ...
    def stocks(self, *, market: int) -> pd.DataFrame | None: ...


class MootdxConnection:
    """一条复用的 mootdx 连接：首次调用建连，协议 / 连接异常重连一次。"""

    def __init__(self, *, timeout: int = 15) -> None:
        self._client: MootdxClient | None = None
        self._timeout = timeout

    def bars(self, *, symbol: str, frequency: int, offset: int, start: int) -> pd.DataFrame | None:
        """取一页 K 线（frequency 为 mootdx 频率编码）。"""
        return self._call(
            lambda c: c.bars(symbol=symbol, frequency=frequency, offset=offset, start=start)
        )

    def quotes(self, symbols: list[str]) -> pd.DataFrame | None:
        """批量取实时报价（现价 / 昨收 / 开高低 / 盘口）。"""
        return self._call(lambda c: c.quotes(symbol=symbols))

    def stocks(self, market: int) -> pd.DataFrame | None:
        """取一个市场的证券列表（代码 / 名称，0=深 1=沪）。"""
        return self._call(lambda c: c.stocks(market=market))

    def _call(
        self, fn: Callable[[MootdxClient], pd.DataFrame | None]
    ) -> pd.DataFrame | None:
        for attempt in range(2):
            try:
                return fn(self._get())
            except Exception:
                self._client = None  # 断开，下次 _get 重连
                if attempt:
                    raise
        return None

    def _get(self) -> MootdxClient:
        if self._client is None:
            self._client = Quotes.factory(market="std", timeout=self._timeout)
        assert self._client is not None
        return self._client
