"""ETF 名称查询：akshare ``fund_etf_spot_em`` 全量拉取 + 内存缓存（TTL 12h）。

首次查拉全量 ETF（代码→名称）缓存，后续查内存。全量约几百只，首次 2~3 秒，
之后 12 小时内走缓存。关注列表输入代码时用它自动填名称。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

_CACHE_TTL = timedelta(hours=12)


class EtfInfoCache:
    """代码→名称 内存缓存，首次查拉全量。"""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._ts: datetime | None = None

    def get_name(self, symbol: str) -> str | None:
        self._ensure()
        return self._cache.get(symbol)

    def invalidate(self) -> None:
        """清缓存（测试 / 强制刷新用）。"""
        self._cache = {}
        self._ts = None

    def _ensure(self) -> None:
        if self._ts is not None and datetime.now() - self._ts < _CACHE_TTL:
            return
        df: pd.DataFrame = ak.fund_etf_spot_em()
        cache: dict[str, str] = {}
        for code, name in zip(df["代码"], df["名称"], strict=True):
            cache[str(code)] = str(name)
        self._cache = cache
        self._ts = datetime.now()


_cache = EtfInfoCache()


def get_etf_name(symbol: str) -> str | None:
    """查 ETF 名称。代码不在全量列表里返 None（前端提示未找到）。"""
    return _cache.get_name(symbol)
