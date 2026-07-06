"""领域数据模型：订单意图、成交、持仓单元、持仓快照。

全部是不可变（frozen）数据类，方便在纯逻辑里安全传递。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from vgrid.core.enums import OrderKind, Side


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """策略引擎产出的「订单意图」。

    引擎只负责决策产出意图，具体怎么下出去由执行层（回测撮合 / 模拟盘 / 实盘）
    实现，两者解耦。

    Attributes:
        side: 买 / 卖。
        price: 限价单的限价；市价单填参考价（当前价）。
        shares: 份额，整手的整数倍。
        level_index: 这笔订单锚定的网格线序号，用于成交后配对与追踪。
        kind: 限价 / 市价。
    """

    side: Side
    price: Decimal
    shares: int
    level_index: int
    kind: OrderKind = OrderKind.LIMIT

    @property
    def notional(self) -> Decimal:
        """名义成交额（不含手续费）。"""
        return self.price * self.shares


@dataclass(frozen=True, slots=True)
class Fill:
    """一笔成交回报。

    Attributes:
        side: 买 / 卖。
        price: 成交价。
        shares: 成交份额。
        fee: 这笔的手续费。
        level_index: 对应的网格线序号。
        ts: 成交时间；纯逻辑单测里可为 None，回测 / 实盘会填真实时间。
        realized_pnl: 卖出成交的已实现盈亏（卖出净收入 − 对应持仓成本，已扣两边
            手续费）；买入成交为 None。
    """

    side: Side
    price: Decimal
    shares: int
    fee: Decimal
    level_index: int
    ts: datetime | None = None
    realized_pnl: Decimal | None = None

    @property
    def notional(self) -> Decimal:
        """名义成交额（不含手续费）。"""
        return self.price * self.shares

    @property
    def cash_delta(self) -> Decimal:
        """这笔成交对现金的净影响。

        买入：现金减少（成交额 + 手续费）；卖出：现金增加（成交额 − 手续费）。
        """
        if self.side is Side.BUY:
            return -(self.notional + self.fee)
        return self.notional - self.fee


@dataclass(frozen=True, slots=True)
class Lot:
    """一个持仓单元：在某条网格线买入、等着在上一格卖出的一份货。

    Attributes:
        buy_price: 买入价（对应买入网格线）。
        shares: 份额。
        buy_fee: 买入手续费。
        sell_target: 目标卖出价（上一格网格线）。
        level_index: 买入网格线序号。
    """

    buy_price: Decimal
    shares: int
    buy_fee: Decimal
    sell_target: Decimal
    level_index: int

    @property
    def cost(self) -> Decimal:
        """建这份货占用的现金（成交额 + 买入手续费）。"""
        return self.buy_price * self.shares + self.buy_fee


@dataclass(frozen=True, slots=True)
class Position:
    """持仓快照（用于报告 / 状态展示）。

    Attributes:
        shares: 总份额。
        cost: 总成本（含买入手续费）。
    """

    shares: int
    cost: Decimal

    @property
    def avg_cost(self) -> Decimal:
        """每份平均成本；空仓返回 0。"""
        if self.shares == 0:
            return Decimal(0)
        return self.cost / self.shares
