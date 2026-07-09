"""腾讯财经行情 provider（ETF 前复权日线）。

腾讯 fqkline 接口 ``web.ifzq.gtimg.cn``，国内实测稳定（连续 8/8 成功），首尔服务器
也通——海外 IP 不被限，正好补上东财 em 源连不上的缺口。支持前复权 qfq / 后复权
hfq / 不复权，ETF 友好（akshare 没封装腾讯 ETF，自己对接）。

实测行为（2026-07）：
- count 参数上限 640 根；区间内 ≤640 根按日期范围返回全部，>640 取最近 640。
  故按年分段请求再合并（每年约 244 交易日，远低于上限）。
- 字段顺序 ``date, open, close, high, low, volume``（close 在第 3 位，和标准
  ``open, high, low, close`` 不同，映射时挪位置）。
- symbol 前缀：5 开头沪市 ``sh``，其余深市 ``sz``（和 sina 同一套）。
"""

from __future__ import annotations

import warnings
from datetime import date

import requests

from vgrid.core.bar import BarSeries
from vgrid.core.enums import Frame
from vgrid.data.provider import bars_from_columns

_TENCENT_URL = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_MAX_COUNT = 640  # 腾讯单次返回上限（根），区间超限只给最近 N 根
# adjust 选项 -> 返回 JSON 里的 key
_ADJUST_KEY = {"qfq": "qfqday", "hfq": "hfqday", "": "day"}


class TencentProvider:
    """腾讯财经数据源。

    Args:
        adjust: 复权方式，``"qfq"``（默认，前复权）/ ``"hfq"``（后复权）/ ``""``（不复权）。
    """

    def __init__(self, adjust: str = "qfq") -> None:
        if adjust not in _ADJUST_KEY:
            raise ValueError(f"不支持的 adjust：{adjust}（可选 qfq/hfq/空）")
        self._adjust = adjust

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        if frame is not Frame.DAILY:
            raise ValueError(f"腾讯源只支持日线，不支持 {frame}")
        code = _tencent_symbol(symbol)
        all_rows: list[list[str]] = []
        for seg_start, seg_end in _split_by_year(start, end):
            all_rows.extend(self._fetch_segment(code, seg_start, seg_end))
        # 跨段边界可能重叠一天，按日期去重；再交给 bars_from_columns 排序
        by_ts: dict[str, list[str]] = {row[0]: row for row in all_rows}
        ordered = sorted(by_ts.values(), key=lambda r: r[0])
        columns: dict[str, list[str]] = {
            "ts": [r[0] for r in ordered],
            "open": [r[1] for r in ordered],
            "high": [r[3] for r in ordered],
            "low": [r[4] for r in ordered],
            "close": [r[2] for r in ordered],  # 腾讯 close 在第 3 位，挪到标准位置
            "volume": [r[5] for r in ordered],
        }
        bars = bars_from_columns(columns, frame)
        return BarSeries(symbol=symbol, frame=frame, bars=tuple(bars))

    def _fetch_segment(self, code: str, start: date, end: date) -> list[list[str]]:
        """请求一段区间的日线原始行（腾讯返回 6 字段字符串行）。"""
        param = f"{code},day,{start.isoformat()},{end.isoformat()},{_MAX_COUNT},{self._adjust}"
        resp = requests.get(_TENCENT_URL, params={"param": param}, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", {}).get(code, {})
        key = _ADJUST_KEY[self._adjust]
        rows = data.get(key)
        if not rows:
            # 请求前复权 / 后复权但该 key 缺 / 空：有不复权 day 时别静默拿它顶替（会把原始价
            # 当复权价、再和别处 qfq 缓存错位叠加），告警并按无数据处理（review #29）。
            if self._adjust and data.get("day"):
                warnings.warn(
                    f"{code} 腾讯未返回 {self._adjust} 数据（{key} 缺 / 空），"
                    "不静默退回不复权，按无数据处理",
                    stacklevel=2,
                )
            return []
        return [list(r) for r in rows]


def _tencent_symbol(code: str) -> str:
    """纯代码 -> 腾讯前缀代码（5 开头沪市 sh，其余深市 sz）。"""
    return ("sh" if code.startswith("5") else "sz") + code


def _split_by_year(start: date, end: date) -> list[tuple[date, date]]:
    """按年切分 [start, end]，每年一段（每段根数远低于 640 上限）。"""
    segments: list[tuple[date, date]] = []
    year = start.year
    while year <= end.year:
        seg_start = max(start, date(year, 1, 1))
        seg_end = min(end, date(year, 12, 31))
        segments.append((seg_start, seg_end))
        year += 1
    return segments
