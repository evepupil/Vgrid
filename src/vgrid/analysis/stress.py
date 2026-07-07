"""黑天鹅推演 / 风控派生量（FR-6.1~6.4）。纯函数，单测重点。

给定实例当前持仓 + 网格配置，估算：
- **占用/硬上限**：占用额、上限、占比%、兜底剩余%（FR-6.1）。
- **下跌推演**：若行情下跌 d，持仓浮亏 ≈ 当前持仓市值 × d（FR-6.2）——只算「当前持仓被
  标低」，不含下跌途中网格继续补仓的增量（那部分由「最大占用」兜底表达）。
- **破下沿放大区**：跌破下沿后每延伸一格，格距 × ``down_spacing_factor``、金额 ×
  ``down_amount_factor`` 减速补仓（FR-6.3）。两系数都为 1 视作未启用放大区。
- **最大占用**：最坏情况占用 = ``capital_cap``，达上限即停买（FR-6.4）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

_DEFAULT_DROPS: tuple[Decimal, ...] = (Decimal("0.05"), Decimal("0.10"), Decimal("0.20"))


@dataclass(frozen=True, slots=True)
class Occupancy:
    """占用资金 / 硬上限（FR-6.1）。"""

    committed: Decimal
    capital_cap: Decimal
    ratio_pct: Decimal  # 占比 %（0~100）
    buffer_pct: Decimal  # 兜底剩余 %（100 − 占比）


@dataclass(frozen=True, slots=True)
class StressScenario:
    """一档下跌推演（FR-6.2）。"""

    drop_pct: Decimal  # 跌幅，如 0.10 表示 −10%
    scenario_price: Decimal  # 推演价 = 现价 ×(1−跌幅)
    position_loss: Decimal  # 持仓浮亏增量 ≈ 持仓市值 × 跌幅（正数=亏损额）
    projected_unrealized: Decimal  # 推演后浮动盈亏 = 当前浮动 − 浮亏增量


@dataclass(frozen=True, slots=True)
class Amplification:
    """破下沿放大区说明（FR-6.3）。"""

    lower_price: Decimal  # 下沿价（跌破即进放大区）
    down_spacing_factor: Decimal
    down_amount_factor: Decimal
    enabled: bool  # 任一系数 > 1 才算启用放大区
    note: str


@dataclass(frozen=True, slots=True)
class StressReport:
    """风控 / 黑天鹅推演汇总。"""

    occupancy: Occupancy
    scenarios: tuple[StressScenario, ...]
    amplification: Amplification
    max_occupancy: Decimal  # = capital_cap（FR-6.4）


def black_swan_report(
    *,
    current_price: Decimal,
    position_value: Decimal,
    unrealized: Decimal,
    committed: Decimal,
    capital_cap: Decimal,
    lower_price: Decimal,
    down_spacing_factor: Decimal,
    down_amount_factor: Decimal,
    drops: Sequence[Decimal] = _DEFAULT_DROPS,
) -> StressReport:
    """算占用 + 逐档下跌推演 + 放大区说明。"""
    occupancy = _occupancy(committed, capital_cap)
    scenarios = tuple(_scenario(d, current_price, position_value, unrealized) for d in drops)
    amplification = _amplification(lower_price, down_spacing_factor, down_amount_factor)
    return StressReport(
        occupancy=occupancy,
        scenarios=scenarios,
        amplification=amplification,
        max_occupancy=capital_cap,
    )


def _occupancy(committed: Decimal, capital_cap: Decimal) -> Occupancy:
    raw = committed / capital_cap * 100 if capital_cap > 0 else Decimal(0)
    ratio = max(Decimal(0), min(Decimal(100), raw))
    return Occupancy(
        committed=committed,
        capital_cap=capital_cap,
        ratio_pct=ratio,
        buffer_pct=Decimal(100) - ratio,
    )


def _scenario(
    drop: Decimal, current_price: Decimal, position_value: Decimal, unrealized: Decimal
) -> StressScenario:
    position_loss = position_value * drop
    return StressScenario(
        drop_pct=drop,
        scenario_price=current_price * (Decimal(1) - drop),
        position_loss=position_loss,
        projected_unrealized=unrealized - position_loss,
    )


def _amplification(
    lower_price: Decimal, down_spacing: Decimal, down_amount: Decimal
) -> Amplification:
    enabled = down_spacing > 1 or down_amount > 1
    if enabled:
        note = f"跌破下沿后每延伸一格：格距 ×{down_spacing}、金额 ×{down_amount} 减速补仓"
    else:
        note = "未启用放大区：跌破下沿后按等距等额继续补仓，直至占满资金上限停买"
    return Amplification(
        lower_price=lower_price,
        down_spacing_factor=down_spacing,
        down_amount_factor=down_amount,
        enabled=enabled,
        note=note,
    )
