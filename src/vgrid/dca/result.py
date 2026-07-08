"""定投回测结果数据结构：成交、权益曲线、指标。

权益曲线复用 ``backtest.EquityPoint``（cash + 持仓市值 + 权益），和网格同结构，方便
最大回撤、对比等复用同一套算法。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import Bar


@dataclass(frozen=True, slots=True)
class DcaTrade:
    """一笔定投买入成交。"""

    ts: datetime
    price: Decimal  # 成交价（执行 K 线 open）
    shares: int
    notional: Decimal  # 成交额（price × shares）
    fee: Decimal
    multiplier: Decimal  # 本次金额倍数（固定=1；加码 / 偏离可 ≠1）

    @property
    def cash_out(self) -> Decimal:
        """这笔占用的现金（成交额 + 手续费）。"""
        return self.notional + self.fee


@dataclass(frozen=True, slots=True)
class SkippedBuy:
    """一次被跳过的定投（买不满一手 / 触顶 / 现金不足），记下来便于复盘。"""

    ts: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class DcaMetrics:
    """定投绩效指标。

    Attributes:
        initial_cash: 账户起始现金。
        invested_amount: 累计投入本金（成交额之和，不含手续费）。
        final_cash: 期末剩余现金。
        final_market_value: 期末持仓市值（末根收盘价估）。
        final_equity: 期末总权益 = 现金 + 持仓市值。
        profit: 账户净利 = 末权益 − 起始现金（已含手续费）。
        profit_on_invested: 已投入资金赚了多少 = 持仓市值 − 累计投入（未扣买入费，费单列）。
        profit_rate_on_invested: profit_on_invested / 累计投入。
        xirr: 分批投入的真实年化（无解为 None）。
        max_drawdown: 逐 K 权益的最大回撤。
        total_fee: 累计手续费。
        n_buys: 实际买入次数。
        skipped_count: 被跳过的定投次数。
        buy_hold_return: 同笔起始现金首根开盘买满、持有到末根收盘的收益率（对照）。
    """

    initial_cash: Decimal
    invested_amount: Decimal
    final_cash: Decimal
    final_market_value: Decimal
    final_equity: Decimal
    profit: Decimal
    profit_on_invested: Decimal
    profit_rate_on_invested: Decimal
    xirr: Decimal | None
    max_drawdown: Decimal
    total_fee: Decimal
    n_buys: int
    skipped_count: int
    buy_hold_return: Decimal


@dataclass(frozen=True, slots=True)
class DcaResult:
    """一次定投回测的完整结果。"""

    trades: tuple[DcaTrade, ...]
    equity_curve: tuple[EquityPoint, ...]
    bars: tuple[Bar, ...]
    metrics: DcaMetrics
    skipped: tuple[SkippedBuy, ...]
