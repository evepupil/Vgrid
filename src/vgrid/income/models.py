"""income 层共享值对象：分红事件、净值点、费用信息。

这些是 series / metrics（纯逻辑）和 dividends / nav / expenses（I/O）都要用的输入原语，
单独放一处，避免纯逻辑层反过来依赖 I/O 层。全为不可变 dataclass，金额 / 费率一律 ``Decimal``。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class DividendEvent:
    """一次分红事件（已标准化，脱离东财原始列名）。

    Attributes:
        register_date: 权益登记日（持有到这天才享这次分红）。
        ex_date: 除息日期（当日价格除息跳空，用来解释未复权价的缺口）。
        pay_date: 分红发放日（现金到账日，用于现金到账与再投资）。
        per_share: 每份分红（元 / 份）。
    """

    register_date: date
    ex_date: date
    pay_date: date
    per_share: Decimal

    def __post_init__(self) -> None:
        if self.per_share <= 0:
            raise ValueError(f"每份分红必须为正：{self.per_share}")
        if self.pay_date < self.register_date:
            raise ValueError(
                f"分红发放日不能早于权益登记日：{self.pay_date} < {self.register_date}",
            )


@dataclass(frozen=True, slots=True)
class NavPoint:
    """某日基金净值。

    Attributes:
        day: 净值日期。
        unit_nav: 单位净值（可和场内价做折溢价观察）。
        acc_nav: 累计净值（含历史分红，作长期表现校验基准）。
    """

    day: date
    unit_nav: Decimal
    acc_nav: Decimal

    def __post_init__(self) -> None:
        if self.unit_nav <= 0:
            raise ValueError(f"单位净值必须为正：{self.unit_nav}")
        if self.acc_nav <= 0:
            raise ValueError(f"累计净值必须为正：{self.acc_nav}")


@dataclass(frozen=True, slots=True)
class ExpenseInfo:
    """基金费用（年费率）。拿不到就整体标 unknown，报告只展示不额外扣费。

    Attributes:
        management_rate: 管理费率（年）。
        custody_rate: 托管费率（年）。
        sales_rate: 销售服务费率（年）。
        total_rate: 合计年费率；None 表示未知。
        source: 费用来源说明（数据源名 / ``unknown``）。
        updated: 费用更新时间（ISO 字符串或 None）。
    """

    management_rate: Decimal | None
    custody_rate: Decimal | None
    sales_rate: Decimal | None
    total_rate: Decimal | None
    source: str
    updated: str | None

    @property
    def is_unknown(self) -> bool:
        """合计年费率拿不到就算未知（报告显示 unknown、不额外扣费）。"""
        return self.total_rate is None

    @classmethod
    def unknown(cls) -> ExpenseInfo:
        """构造一个"费用未知"占位。"""
        return cls(
            management_rate=None,
            custody_rate=None,
            sales_rate=None,
            total_rate=None,
            source="unknown",
            updated=None,
        )
