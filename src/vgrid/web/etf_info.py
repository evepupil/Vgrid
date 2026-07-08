"""ETF 名称查询：通达信 ``stocks()`` 全市场列表 + 内存缓存（TTL 12h）。

首次查拉沪深全市场证券（代码→名称）缓存，后续查内存。东财现货表
（``fund_etf_spot_em``）海外常年超时，换成通达信协议（稳定不限 IP）。全市场比只拉 ETF
现货表重（沪 + 深各几千只），故缓存 12 小时；关注列表输入代码时用它自动填名称。
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Protocol

from vgrid.data.mootdx_quotes import MootdxQuotes

_CACHE_TTL = timedelta(hours=12)


class NameSource(Protocol):
    """代码→名称 数据源（默认 mootdx，测试可注入 fake）。"""

    def names(self) -> dict[str, str]: ...


class EtfInfoCache:
    """代码→名称 内存缓存，首次查拉全量。

    FastAPI 把同步路由放线程池跑，冷缓存时多个请求会同时触发拉取、还会读到半填缓存。
    用 double-checked locking：命中无锁、未命中才串行拉取（review #33）。
    """

    def __init__(self, quotes: NameSource | None = None) -> None:
        self._quotes: NameSource = quotes or MootdxQuotes()
        self._cache: dict[str, str] = {}
        self._ts: datetime | None = None
        self._lock = threading.Lock()

    def get_name(self, symbol: str) -> str | None:
        self._ensure()
        return self._cache.get(symbol)

    def invalidate(self) -> None:
        """清缓存（测试 / 强制刷新用）。"""
        with self._lock:
            self._cache = {}
            self._ts = None

    def _ensure(self) -> None:
        if self._ts is not None and datetime.now() - self._ts < _CACHE_TTL:
            return
        with self._lock:
            # 再判一次：可能别的线程刚拉完
            if self._ts is not None and datetime.now() - self._ts < _CACHE_TTL:
                return
            names = self._quotes.names()
            if names:  # 拉空（连接失败）不刷缓存，留着下次重试
                self._cache = names
                self._ts = datetime.now()


_cache = EtfInfoCache()


def get_etf_name(symbol: str) -> str | None:
    """查 ETF 名称。代码不在全量列表里返 None（前端提示未找到）。"""
    return _cache.get_name(symbol)
