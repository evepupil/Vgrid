"""回测结果数据结构：权益曲线、绩效指标、回测快照。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.core.models import Fill


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """某根 K 线收盘时的权益快照。

    Attributes:
        ts: 时间。
        cash: 现金余额（初始资金 + 累计净现金流）。
        position_value: 持仓按当根收盘价估值。
        equity: 总权益 = cash + position_value。
    """

    ts: datetime
    cash: Decimal
    position_value: Decimal
    equity: Decimal


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """绩效指标（金额与比率统一用 Decimal，便于精确展示与对比）。"""

    initial_cash: Decimal
    final_equity: Decimal
    total_return: Decimal
    annualized_return: Decimal
    max_drawdown: Decimal
    sharpe: Decimal
    win_rate: Decimal
    profit_loss_ratio: Decimal
    n_buys: int
    n_sells: int
    total_fee: Decimal
    buy_hold_return: Decimal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """一次回测的完整结果。"""

    fills: tuple[Fill, ...]
    equity_curve: tuple[EquityPoint, ...]
    bars: tuple[Bar, ...]
    metrics: BacktestMetrics
