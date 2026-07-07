"""Parquet 本地行情缓存。

每个 ``(symbol, frame)`` 一个 parquet 文件，存全量已下载 K 线（按 ts 升序）。读回时
复用 ``data.provider.bars_from_columns`` 把列式表还原成 Bar——和 akshare 走同一条
转换路径，缓存读写与数据源解耦。

价格 / 成交量以 string 存（``Decimal`` 无损往返）；ts 存 timestamp。
"""

from __future__ import annotations

import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.data.provider import bars_from_columns

_CACHE_COLUMNS = ("ts", "open", "high", "low", "close", "volume")
_SCHEMA = pa.schema(
    [
        ("ts", pa.timestamp("ns")),
        ("open", pa.string()),
        ("high", pa.string()),
        ("low", pa.string()),
        ("close", pa.string()),
        ("volume", pa.string()),
    ]
)


class ParquetCache:
    """每个 (symbol, frame) 一个 Parquet 文件，存全量已下载 K 线。"""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, frame: Frame) -> Path:
        return self._dir / f"{symbol}_{frame.value}.parquet"

    def load(self, symbol: str, frame: Frame) -> BarSeries | None:
        """读缓存；文件不存在返回 None。"""
        path = self._path(symbol, frame)
        if not path.exists():
            return None
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        columns: dict[str, list[object]] = table.to_pydict()
        bars = bars_from_columns(columns, frame)
        return BarSeries(symbol=symbol, frame=frame, bars=tuple(bars))

    def save(self, series: BarSeries) -> None:
        """覆盖写整个文件（series 应已是合并去重后的全量）。

        先写临时文件再 ``os.replace`` 原子替换：写一半被杀 / 断电 / 磁盘满时，原文件
        不受影响，不会留下半残的 parquet 让下次 ``load`` 崩。
        """
        table = _bars_to_table(series.bars)
        path = self._path(series.symbol, series.frame)
        tmp = path.with_name(path.name + ".tmp")
        pq.write_table(table, tmp)  # type: ignore[no-untyped-call]
        os.replace(tmp, path)


def _bars_to_table(bars: tuple[Bar, ...]) -> pa.Table:
    data: dict[str, list[object]] = {col: [] for col in _CACHE_COLUMNS}
    for b in bars:
        data["ts"].append(b.ts)
        data["open"].append(str(b.open))
        data["high"].append(str(b.high))
        data["low"].append(str(b.low))
        data["close"].append(str(b.close))
        data["volume"].append(str(b.volume))
    return pa.table(data, schema=_SCHEMA)
