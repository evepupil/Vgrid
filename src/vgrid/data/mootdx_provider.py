"""mootdx 行情 provider（通达信协议，分钟线，稳定不限 IP）。

走通达信 TCP 7709 协议，不依赖东财/腾讯那些 HTTP host，服务器多可切换，实测连接+
拉取 5/5 稳定。支持 1 分钟（``Frame.MINUTE``）和 5 分钟（``Frame.M5``）。akshare 的
ETF 分钟线走东财 host 不稳，腾讯分钟线 host 也连不上，mootdx 是稳定的分钟源。

历史深度（159920 实测 2026-07）：
- 1 分钟线：约 2.5 个月（2026-04-22 起）。
- 5 分钟线：约 1 年 8 个月（2024-11-11 起）。

mootdx 单次最多 800 根，翻页（``start`` 累加）拉全量，本地按区间过滤去重。
返回不复权原始价——跨除权日有缺口，复权后续用 mootdx Affair 接口做。
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from vgrid.core.bar import BarSeries
from vgrid.core.enums import Frame
from vgrid.data.mootdx_client import MootdxConnection
from vgrid.data.provider import bars_from_columns

_PAGE = 800  # 通达信协议单次返回上限（根）
_MAX_PAGES = 400  # 安全上限（800×400=32 万根，5 分钟线近两年也够）
# Frame -> mootdx frequency 编码：7=1 分钟，0=5 分钟
_FREQ: dict[Frame, int] = {Frame.MINUTE: 7, Frame.M5: 0}


class MootdxProvider:
    """通达信行情数据源（分钟线）。

    连接走 ``MootdxConnection``（首次 fetch 建连、后续复用、异常重连一次）。日线不走这里，
    走腾讯前复权源（``TencentProvider``），见 ``loader`` 的默认路由。
    """

    def __init__(self) -> None:
        self._conn = MootdxConnection()

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        if frame not in _FREQ:
            raise ValueError(f"mootdx 只支持分钟线（1m/5m），不支持 {frame}")
        frames = self._fetch_all(symbol, _FREQ[frame], start)
        if not frames:
            return BarSeries(symbol=symbol, frame=frame, bars=())
        full = pd.concat(frames)
        full = full[~full.index.duplicated(keep="last")].sort_index()
        mask = (full.index.date >= start) & (full.index.date <= end)
        full = full[mask]
        columns = {
            "ts": [str(idx) for idx in full.index],
            "open": list(full["open"]),
            "high": list(full["high"]),
            "low": list(full["low"]),
            "close": list(full["close"]),
            "volume": list(full["volume"]),
        }
        bars = bars_from_columns(columns, frame)
        return BarSeries(symbol=symbol, frame=frame, bars=tuple(bars))

    def _fetch_all(self, symbol: str, freq: int, start: date) -> list[pd.DataFrame]:
        """翻页拉全量，直到覆盖 start 日期或无数据。"""
        frames: list[pd.DataFrame] = []
        pos = 0
        for _ in range(_MAX_PAGES):
            df = self._bars(symbol, freq, pos)
            if df is None or len(df) == 0:
                break
            frames.append(df)
            if df.index[0].date() < start:
                break  # 已覆盖请求起点
            pos += _PAGE
        return frames

    def _bars(self, symbol: str, freq: int, start: int) -> pd.DataFrame | None:
        """调 mootdx client.bars（连接管理 + 重连交给 MootdxConnection）。"""
        return self._conn.bars(symbol=symbol, frequency=freq, offset=_PAGE, start=start)


# 关注验证用的单例（连接复用）。模块加载不连接，首次 fetch 才连。
_validator = MootdxProvider()


def symbol_exists(symbol: str) -> bool:
    """用 mootdx 拉近期 5 分钟线验证代码有效（通达信协议，稳定不限 IP）。

    有数据 = 代码是有效 ETF；无数据 / 连接异常都返 False（拦下让用户核对代码）。
    相比 ``fund_etf_spot_em``（东财现货源，海外不稳/超时），通达信协议在海外稳定。
    """
    end = date.today()
    start = end - timedelta(days=5)
    try:
        series = _validator.fetch(symbol, start, end, Frame.M5)
    except Exception:  # mootdx 连接 / 协议任意异常都视作"验不住"，拦下
        return False
    return len(series.bars) > 0
