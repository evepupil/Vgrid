"""统一 K 线（Bar）行情模型。

日线、分钟线共用同一个 ``Bar`` 结构，回测器只认 ``BarSeries``，不关心数据来自
akshare 还是别的源。行情是和 ``Order`` / ``Fill`` 同级的领域原语，放 core 层，
``data`` 和 ``backtest`` 都依赖它，避免循环依赖。

全系统金额 / 价格一律用 ``Decimal``，所以 Bar 的 OHLC 也是 ``Decimal``，不在边界处
用 float 凑合。从外部数据源（DataFrame 等）转 Bar 的工作交给 ``data`` 层，core 只
定义原语与校验，不绑定具体数据源格式。
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from vgrid.core.enums import Frame


def _check_price(value: Decimal, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} 必须为正：{value}")


@dataclass(frozen=True, slots=True)
class Bar:
    """一根 K 线。

    Attributes:
        ts: 这根 K 线的开始时刻（开盘时间）。
        open: 开盘价。
        high: 最高价。
        low: 最低价。
        close: 收盘价。
        volume: 成交量（≥ 0；停牌等无数据时可填 0）。
    """

    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        _check_price(self.open, "open")
        _check_price(self.high, "high")
        _check_price(self.low, "low")
        _check_price(self.close, "close")
        if self.volume < 0:
            raise ValueError(f"成交量不能为负：{self.volume}")
        # OHLC 互检：high 必须是四价最高、low 必须是最低。
        if self.high < self.open or self.high < self.close or self.high < self.low:
            raise ValueError(f"high 必须不低于 O/C/L：{self}")
        if self.low > self.open or self.low > self.close or self.low > self.high:
            raise ValueError(f"low 必须不高于 O/C/H：{self}")


@dataclass(frozen=True, slots=True)
class BarSeries:
    """一个标的、某个周期下的一串 K 线，按时间从早到晚排好。

    Attributes:
        symbol: 标的代码，如 "159920"。
        frame: K 线周期。
        bars: 从早到晚的 K 线（时间严格递增）。
    """

    symbol: str
    frame: Frame
    bars: tuple[Bar, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol 不能为空")
        # 允许空序列（数据还没下），但一旦有，必须严格递增。
        for prev, cur in zip(self.bars[:-1], self.bars[1:], strict=True):
            if cur.ts <= prev.ts:
                raise ValueError(f"bars 必须按时间严格递增：{prev.ts} -> {cur.ts}")

    def __len__(self) -> int:
        return len(self.bars)

    def __iter__(self) -> Iterator[Bar]:
        return iter(self.bars)

    def __getitem__(self, index: int) -> Bar:
        return self.bars[index]
