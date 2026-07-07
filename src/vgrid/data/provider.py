"""行情数据源协议 + 列式数据转 Bar 的纯函数。

``BarProvider`` 定义「取数」接口（akshare / 未来别的源各写各的实现）；
``bars_from_columns`` 把「列名 → 序列」的列式数据转成按时间升序的 Bar 列表，是
纯函数，单测重点（不碰 pandas / akshare / 网络）。

akshare 返回 DataFrame、Parquet 读回来也是列式表，两者都先归一成列 dict 再喂给
``bars_from_columns``，这样转换逻辑只有一份。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame


@runtime_checkable
class BarProvider(Protocol):
    """行情数据源：取一个标的、某周期、某区间的 K 线。"""

    def fetch(self, symbol: str, start: date, end: date, frame: Frame) -> BarSeries:
        """下载 [start, end] 闭区间内的日线 / 分钟线。"""
        ...


def bars_from_columns(columns: Mapping[str, Sequence[object]], frame: Frame) -> list[Bar]:
    """把列式数据（每个 key 对应一列）转成按时间升序、时间戳唯一的 Bar 列表。

    期望 keys：``ts / open / high / low / close / volume``。
    ``ts`` 接受 str / datetime / date / pandas.Timestamp（先 ``str()`` 归一再
    ``fromisoformat`` 解析）；价格列接受任意可转 ``Decimal`` 的值。

    单次数据里若出现重复时间戳（分钟线跨段拼接时 akshare 偶发），按「后到覆盖前到」
    去重——和 ``loader._merge`` 同口径。不去重会让下游 ``BarSeries`` 的严格递增校验直接崩。
    """
    keys = ("ts", "open", "high", "low", "close", "volume")
    missing = [k for k in keys if k not in columns]
    if missing:
        raise ValueError(f"列数据缺少字段：{missing}")
    n = len(columns["ts"])
    if any(len(columns[k]) != n for k in keys):
        raise ValueError("各列长度不一致")

    by_ts: dict[datetime, Bar] = {}
    for i in range(n):
        bar = Bar(
            ts=_parse_ts(columns["ts"][i]),
            open=Decimal(str(columns["open"][i])),
            high=Decimal(str(columns["high"][i])),
            low=Decimal(str(columns["low"][i])),
            close=Decimal(str(columns["close"][i])),
            volume=Decimal(str(columns["volume"][i])),
        )
        by_ts[bar.ts] = bar
    return sorted(by_ts.values(), key=lambda b: b.ts)


def _parse_ts(value: object) -> datetime:
    """把 ts 列的一个值归一成 datetime。"""
    if isinstance(value, datetime):
        return value
    text = str(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError as e:
        raise ValueError(f"无法解析时间：{value!r}") from e
