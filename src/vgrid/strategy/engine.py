"""网格引擎：纯逻辑状态机。

驱动方式（M1）：喂一串价格 tick，引擎按「跌买涨卖」产出成交。
- ``start(price)``：按建仓模式初始化（中枢建仓 / 零底仓）。
- ``step(price)``：价格更新，返回本次触发的成交列表。

成交假设：挂在某条网格线上的限价单，价格触到就以该线价格成交。对流动性好、
单笔又小的 ETF 网格来说，这个假设是贴合真实的（挂单被触发即以限价成交）。

引擎自己维护一份最小账本（占用资金、持仓单元、已实现盈亏、手续费），供回测和
报告读取；实际下单由执行层负责，两者解耦。回测直接复用本引擎，实盘只需另写一个
执行适配器读取 ``desired_orders`` 并回喂成交，策略逻辑一行不改。

关键状态：
- ``_lots``：未平仓的持仓单元，用「卖出目标价」做键——每个格子（相邻两线之间）
  同一时刻至多一份货，卖出目标价天然唯一，用它做键最稳，不受阶梯上移 / 延伸后
  序号变化的影响。
"""

from decimal import Decimal

from vgrid.core.config import GridConfig
from vgrid.core.enums import BaseBuildMode, Side
from vgrid.core.models import Fill, Lot, OrderIntent, Position
from vgrid.core.money import shares_for_amount
from vgrid.strategy.ladder import Ladder


class GridEngine:
    """网格策略状态机（纯逻辑，不做 I/O）。"""

    def __init__(self, config: GridConfig) -> None:
        self._config = config
        self._ladder = Ladder(config)
        self._lots: dict[Decimal, Lot] = {}
        self._committed = Decimal(0)
        self._realized_pnl = Decimal(0)
        self._total_fee = Decimal(0)
        self._cash_flow = Decimal(0)
        self._last_price: Decimal | None = None
        self._started = False

    # ------------------------------------------------------------------ 只读视图

    @property
    def config(self) -> GridConfig:
        return self._config

    @property
    def ladder(self) -> Ladder:
        return self._ladder

    @property
    def committed(self) -> Decimal:
        """当前占用资金（未平仓单元的成本合计，含买入手续费）。"""
        return self._committed

    @property
    def realized_pnl(self) -> Decimal:
        """累计已实现盈亏（每完成一次卖出结算一次，已扣两边手续费）。"""
        return self._realized_pnl

    @property
    def total_fee(self) -> Decimal:
        """累计手续费。"""
        return self._total_fee

    @property
    def cash_flow(self) -> Decimal:
        """交易带来的净现金流（买为负、卖为正，已含手续费）。"""
        return self._cash_flow

    @property
    def open_lots(self) -> int:
        """未平仓单元数量。"""
        return len(self._lots)

    @property
    def open_positions(self) -> tuple[Lot, ...]:
        """未平仓单元快照，按卖出目标价从低到高。"""
        return tuple(self._lots[target] for target in sorted(self._lots))

    @property
    def position(self) -> Position:
        """当前持仓快照。"""
        shares = sum(lot.shares for lot in self._lots.values())
        cost = sum((lot.cost for lot in self._lots.values()), Decimal(0))
        return Position(shares=shares, cost=cost)

    # ------------------------------------------------------------------ 驱动接口

    def start(self, price: Decimal) -> list[Fill]:
        """按建仓模式初始化，返回建仓成交（零底仓则为空）。"""
        if self._started:
            raise RuntimeError("引擎已启动，不能重复 start")
        # 把阶梯窗口对齐到起始价
        if price > self._ladder.top:
            self._ladder.shift_up_to(price)
        elif price < self._ladder.bottom:
            self._ladder.ensure_covers_down_to(price)

        fills: list[Fill] = []
        if self._config.base_build_mode is BaseBuildMode.CENTER:
            fills = self._build_center(price, ratio=Decimal(1))

        self._last_price = price
        self._started = True
        return fills

    def step(self, price: Decimal) -> list[Fill]:
        """价格更新一格，返回本次触发的成交。"""
        if not self._started:
            raise RuntimeError("引擎未启动，请先 start")
        last = self._last_price
        assert last is not None  # _started 为真时必已赋值
        fills: list[Fill] = []

        if price < last:
            fills = self._fill_buys_descending(from_price=last, to_price=price)
        elif price > last:
            fills = self._fill_sells_ascending(from_price=last, to_price=price)

        self._last_price = price
        return fills

    def desired_orders(self, price: Decimal) -> list[OrderIntent]:
        """当前状态下「应该挂着」的限价单集合（供实盘执行层对账用）。

        与 ``step`` 共用同一套决策口径：卖单挂在每个持仓单元的目标价；买单挂在
        现价下方的空格子上，受资金上限约束（就近优先，占满即止）。
        """
        orders: list[OrderIntent] = []
        for target in sorted(self._lots):
            lot = self._lots[target]
            orders.append(
                OrderIntent(Side.SELL, target, lot.shares, self._ladder.index_of(target))
            )

        self._ladder.ensure_covers_down_to(price)
        projected = self._committed
        for line in sorted(self._ladder.lines, key=lambda ln: ln.price, reverse=True):
            if line.price >= price:
                continue
            target_line = self._ladder.line_above(line.price)
            if target_line is None or target_line.price in self._lots:
                continue
            shares = shares_for_amount(line.buy_amount, line.price, self._config.lot_size)
            if shares <= 0:
                continue
            cost = self._estimate_cost(line.price, shares)
            if projected + cost > self._config.capital_cap:
                break
            projected += cost
            orders.append(
                OrderIntent(Side.BUY, line.price, shares, self._ladder.index_of(line.price))
            )
        return orders

    # ------------------------------------------------------------------ 内部逻辑

    def _fill_buys_descending(self, from_price: Decimal, to_price: Decimal) -> list[Fill]:
        """价格下行：对区间 (to_price, from_price) 内的空格子逐个买入（就近优先）。"""
        self._ladder.ensure_covers_down_to(to_price)
        fills: list[Fill] = []
        for line in sorted(self._ladder.lines, key=lambda ln: ln.price, reverse=True):
            if line.price >= from_price or line.price < to_price:
                continue
            target_line = self._ladder.line_above(line.price)
            if target_line is None or target_line.price in self._lots:
                continue
            shares = shares_for_amount(line.buy_amount, line.price, self._config.lot_size)
            if shares <= 0:
                continue
            fill = self._execute_buy(line.price, shares, target_line.price)
            if fill is None:
                continue  # 触及资金上限，停止在更低的格子继续买
            fills.append(fill)
        return fills

    def _fill_sells_ascending(self, from_price: Decimal, to_price: Decimal) -> list[Fill]:
        """价格上行：卖出目标价落在区间 (from_price, to_price] 内的持仓单元。"""
        fills: list[Fill] = []
        for target in sorted(self._lots):
            if from_price < target <= to_price:
                fills.append(self._execute_sell(self._lots[target]))
        if to_price > self._ladder.top:
            self._ladder.shift_up_to(to_price)
            if self._config.upper_rebuild_ratio > 0:
                fills.extend(self._build_center(to_price, self._config.upper_rebuild_ratio))
        return fills

    def _build_center(self, price: Decimal, ratio: Decimal) -> list[Fill]:
        """中枢建仓：把现价上方每个格子的份额按 ``price`` 市价买齐（份额 ×ratio）。"""
        fills: list[Fill] = []
        for line in self._ladder.lines:
            target = line.price
            if target <= price or target in self._lots:
                continue
            shares = shares_for_amount(
                self._config.per_grid_amount * ratio, price, self._config.lot_size
            )
            if shares <= 0:
                continue
            fill = self._execute_buy(price, shares, target)
            if fill is None:
                break  # 资金占满，上方更高的格子也不再建
            fills.append(fill)
        return fills

    def _estimate_cost(self, price: Decimal, shares: int) -> Decimal:
        notional = price * shares
        return notional + self._config.fee.compute(notional)

    def _execute_buy(
        self,
        price: Decimal,
        shares: int,
        sell_target: Decimal,
    ) -> Fill | None:
        """成交一笔买入并登记持仓单元；超出资金上限则不成交，返回 None。"""
        notional = price * shares
        fee = self._config.fee.compute(notional)
        cost = notional + fee
        if self._committed + cost > self._config.capital_cap:
            return None
        level_index = self._ladder.index_of(sell_target)
        lot = Lot(
            buy_price=price,
            shares=shares,
            buy_fee=fee,
            sell_target=sell_target,
            level_index=level_index,
        )
        self._lots[sell_target] = lot
        self._committed += cost
        self._total_fee += fee
        self._cash_flow -= cost
        return Fill(Side.BUY, price, shares, fee, level_index)

    def _execute_sell(self, lot: Lot) -> Fill:
        """成交一笔卖出并结算持仓单元。"""
        notional = lot.sell_target * lot.shares
        fee = self._config.fee.compute(notional)
        proceeds = notional - fee
        self._realized_pnl += proceeds - lot.cost
        self._committed -= lot.cost
        self._total_fee += fee
        self._cash_flow += proceeds
        del self._lots[lot.sell_target]
        return Fill(Side.SELL, lot.sell_target, lot.shares, fee, lot.level_index)
