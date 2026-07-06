"""akshare 行情 provider（东方财富 ETF 接口）。

akshare 的接口签名 / 返回列名随版本会变；本模块把 akshare 调用与中文列名适配集中
在这里，转换逻辑复用 ``data.provider.bars_from_columns``。真实环境跑前请确认 akshare
版本对得上（接口列名见 ``_COL_MAP``）。
"""

from __future__ import annotations

from datetime import date

import akshare as ak
import pandas as pd

from vgrid.core.bar import BarSeries
from vgrid.core.enums import Frame
from vgrid.data.provider import bars_from_columns

# akshare ETF 接口中文列名 -> 标准列名
_COL_MAP = {
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
}


class AkshareProvider:
    """akshare 数据源实现。"""

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
        df: pd.DataFrame = ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        return _df_to_columns(df, ts_col="日期")

    def _fetch_minute(self, symbol: str, start: date, end: date) -> dict[str, list[object]]:
        df: pd.DataFrame = ak.fund_etf_hist_min_em(
            symbol=symbol,
            period="1",
            start_date=f"{start.isoformat()} 09:30:00",
            end_date=f"{end.isoformat()} 15:00:00",
        )
        return _df_to_columns(df, ts_col="时间")


def _df_to_columns(df: pd.DataFrame, ts_col: str) -> dict[str, list[object]]:
    """akshare DataFrame -> 标准列 dict（ts/open/high/low/close/volume）。"""
    col_map = {**_COL_MAP, ts_col: "ts"}
    missing = [c for c in col_map if c not in df.columns]
    if missing:
        raise ValueError(f"akshare 返回缺少列 {missing}；实际列：{list(df.columns)}")
    return {new: list(df[old]) for old, new in col_map.items()}
