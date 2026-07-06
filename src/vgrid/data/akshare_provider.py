"""akshare 行情 provider。

支持两个日线数据源（``source`` 参数）：
- ``"sina"``（默认）：新浪源 ``fund_etf_hist_sina``，走新浪 host，实测稳定可用。
- ``"em"``：东方财富 ``fund_etf_hist_em``，列名中文。

分钟线只有东财源（``fund_etf_hist_min_em``），不受 ``source`` 影响。

akshare 接口签名 / 列名随版本会变；适配集中在本模块，转换走 ``data.provider.bars_from_columns``。
"""

from __future__ import annotations

from datetime import date

import akshare as ak
import pandas as pd

from vgrid.core.bar import BarSeries
from vgrid.core.enums import Frame
from vgrid.data.provider import bars_from_columns

# 东财源中文列名 -> 标准列名
_COL_MAP_EM = {
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
}
# 新浪源列名已是英文，identity 映射
_COL_MAP_SINA = {
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
}


class AkshareProvider:
    """akshare 数据源实现。

    Args:
        source: 日线数据源，``"sina"``（默认，新浪）或 ``"em"``（东财）。
    """

    def __init__(self, source: str = "sina") -> None:
        if source not in ("sina", "em"):
            raise ValueError(f"不支持的 source：{source}（可选 sina / em）")
        self._source = source

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        if frame is Frame.DAILY:
            columns = self._fetch_daily(symbol, start, end)
        elif frame is Frame.MINUTE:
            columns = self._fetch_minute(symbol, start, end)
        else:
            raise ValueError(f"不支持的周期：{frame}")
        bars = bars_from_columns(columns, frame)
        return BarSeries(symbol=symbol, frame=frame, bars=tuple(bars))

    def _fetch_daily(self, symbol: str, start: date, end: date) -> dict[str, list[object]]:
        if self._source == "sina":
            df: pd.DataFrame = ak.fund_etf_hist_sina(symbol=_sina_symbol(symbol))
            # sina 返回全量历史；date 列可能是 str 或 date 对象，统一转 str 按字典序过滤
            df = df.copy()
            df["date"] = df["date"].astype(str)
            mask = (df["date"] >= start.isoformat()) & (df["date"] <= end.isoformat())
            df = df.loc[mask]
            return _df_to_columns(df, ts_col="date", col_map=_COL_MAP_SINA)
        df = ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        return _df_to_columns(df, ts_col="日期", col_map=_COL_MAP_EM)

    def _fetch_minute(self, symbol: str, start: date, end: date) -> dict[str, list[object]]:
        df = ak.fund_etf_hist_min_em(
            symbol=symbol,
            period="1",
            start_date=f"{start.isoformat()} 09:30:00",
            end_date=f"{end.isoformat()} 15:00:00",
        )
        return _df_to_columns(df, ts_col="时间", col_map=_COL_MAP_EM)


def _sina_symbol(code: str) -> str:
    """纯代码 -> 新浪前缀代码（5 开头沪市 sh，其余深市 sz）。"""
    return ("sh" if code.startswith("5") else "sz") + code


def _df_to_columns(
    df: pd.DataFrame, ts_col: str, col_map: dict[str, str]
) -> dict[str, list[object]]:
    """akshare DataFrame -> 标准列 dict（ts/open/high/low/close/volume）。"""
    full = {**col_map, ts_col: "ts"}
    missing = [c for c in full if c not in df.columns]
    if missing:
        raise ValueError(f"akshare 返回缺少列 {missing}；实际列：{list(df.columns)}")
    return {new: list(df[old]) for old, new in full.items()}
