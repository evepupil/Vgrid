"""实时行情 provider。

``RealtimeProvider`` 是协议；``AkshareRealtimeProvider`` 是 akshare 实现。真实接口名 / 列名
待代理通后实测确认，先按 ``fund_etf_spot_em`` 全量按 symbol 过滤实现（适配集中在本文件，
和 data 层 akshare provider 同思路）。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class RealtimeProvider(Protocol):
    """实时行情：取一个标的的当前价 + 时间戳。"""

    def fetch(self, symbol: str) -> tuple[datetime, Decimal]: ...


class AkshareRealtimeProvider:
    """akshare ETF 实时行情（东方财富实时盘，按 symbol 过滤）。"""

    def fetch(self, symbol: str) -> tuple[datetime, Decimal]:
        import akshare as ak  # noqa: PLC0415  懒导入，避免模块加载依赖网络 / akshare

        df = ak.fund_etf_spot_em()
        row = df[df["代码"] == symbol]
        if row.empty:
            raise ValueError(f"实时行情找不到标的：{symbol}")
        price = Decimal(str(row.iloc[0]["最新价"]))
        return datetime.now(), price
