"""批量回测的结果模型。

一只 ETF 一行（``BatchRow``），全体 + 排序装进 ``BatchResult``。只放数据结构和排序，
不碰 I/O、不跑回测——回测在 ``runner`` 里做。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: CLI --sort 的合法键。xirr/两个收益率越大越好，max_drawdown 越小越好（runner 里特殊处理）。
SORT_CHOICES: tuple[str, ...] = ("xirr", "dca_return", "buy_hold_return", "max_drawdown")


@dataclass(frozen=True, slots=True)
class BatchRow:
    """单只 ETF 的批量回测结果。

    同一份定投配置下，这只 ETF 的定投表现 + 同期一次性买入（buy_hold）对照。
    ``ok=False`` 表示这只没跑成（无数据等），``reason`` 说明原因，指标字段为 None。
    """

    code: str
    name: str
    ok: bool
    reason: str | None = None
    # 定投口径
    dca_return: Decimal | None = None  # 对累计投入本金的收益率
    dca_xirr: Decimal | None = None  # 资金加权真实年化（无解为 None）
    dca_max_drawdown: Decimal | None = None
    invested: Decimal | None = None  # 累计投入本金
    n_buys: int | None = None
    skipped: int | None = None  # 买不满一手跳过的次数
    total_fee: Decimal | None = None
    # 一次性买入对照
    buy_hold_return: Decimal | None = None

    @classmethod
    def failed(cls, code: str, name: str, reason: str) -> BatchRow:
        """构造一条「没跑成」的行。"""
        return cls(code=code, name=name, ok=False, reason=reason)


@dataclass(frozen=True, slots=True)
class BatchResult:
    """全体 ETF 的批量回测结果 + 用的区间信息。"""

    rows: tuple[BatchRow, ...]
    start: str
    end: str
    frame: str
    sort_key: str

    @property
    def ok_rows(self) -> tuple[BatchRow, ...]:
        """跑成的行（有指标的）。"""
        return tuple(r for r in self.rows if r.ok)

    @property
    def failed_rows(self) -> tuple[BatchRow, ...]:
        """没跑成的行（无数据等）。"""
        return tuple(r for r in self.rows if not r.ok)
