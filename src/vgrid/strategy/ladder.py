"""阶梯的可变状态。

``gridlines`` 只算价格（纯函数）；``Ladder`` 在它之上维护「当前这条阶梯」的
可变状态：基准窗口 + 向下延伸的网格线，并提供延伸 / 上移操作。

每条网格线记三样：
- ``price``：价格。
- ``buy_amount``：在这条线买入时用的每格金额（向下延伸的线会按系数放大 / 缩小）。
- ``depth``：0 表示基准窗口内的线，k>0 表示基准下沿之下第 k 层延伸线。
"""

from dataclasses import dataclass
from decimal import Decimal

from vgrid.core.config import GridConfig
from vgrid.core.money import quantize_price
from vgrid.strategy.gridlines import bottom_gap, build_levels, shift_window_up


@dataclass(frozen=True, slots=True)
class GridLine:
    """一条网格线。"""

    price: Decimal
    buy_amount: Decimal
    depth: int


class Ladder:
    """当前阶梯：基准窗口 + 向下延伸，支持追踪上移。"""

    def __init__(self, config: GridConfig) -> None:
        self._config = config
        self._lower = config.lower_price
        self._upper = config.upper_price
        self._lines: list[GridLine] = []
        self._base_gap = Decimal(0)
        self._next_gap = Decimal(0)
        self._ext_depth = 0
        self._build_base()

    def _build_base(self) -> None:
        prices = build_levels(
            self._lower,
            self._upper,
            self._config.grid_count,
            self._config.spacing_mode,
            self._config.price_tick,
        )
        self._lines = [GridLine(p, self._config.per_grid_amount, 0) for p in prices]
        self._base_gap = bottom_gap(prices)
        self._next_gap = self._base_gap
        self._ext_depth = 0

    # --- 只读视图 ---

    @property
    def lines(self) -> list[GridLine]:
        """从低到高的所有网格线。"""
        return self._lines

    @property
    def prices(self) -> list[Decimal]:
        return [ln.price for ln in self._lines]

    @property
    def bottom(self) -> Decimal:
        return self._lines[0].price

    @property
    def top(self) -> Decimal:
        return self._lines[-1].price

    def line_above(self, price: Decimal) -> GridLine | None:
        """严格高于 ``price`` 的最近一条网格线。"""
        for ln in self._lines:
            if ln.price > price:
                return ln
        return None

    def line_below(self, price: Decimal) -> GridLine | None:
        """严格低于 ``price`` 的最近一条网格线。"""
        for ln in reversed(self._lines):
            if ln.price < price:
                return ln
        return None

    def index_of(self, price: Decimal) -> int:
        """价格对应的网格线序号；找不到返回 -1。仅用于展示 / 标注。"""
        for i, ln in enumerate(self._lines):
            if ln.price == price:
                return i
        return -1

    # --- 变更操作 ---

    def ensure_covers_down_to(self, price: Decimal, floor: Decimal | None = None) -> None:
        """向下延伸，直到最低网格线不高于 ``price``（或无法再延伸）。

        延伸幅度由价格实际跌到哪决定，不会无限延伸。``floor`` 给定时不越过它。
        """
        while self.bottom > price:
            if not self._extend_one(floor):
                break

    def _extend_one(self, floor: Decimal | None) -> bool:
        gap = self._next_gap
        new_price = self.bottom - gap
        if new_price <= 0 or (floor is not None and new_price < floor):
            return False
        q = quantize_price(new_price, self._config.price_tick)
        if q >= self.bottom:
            return False
        depth = self._ext_depth + 1
        amount = self._config.per_grid_amount * (self._config.down_amount_factor**depth)
        self._lines.insert(0, GridLine(q, amount, depth))
        self._ext_depth = depth
        self._next_gap = gap * self._config.down_spacing_factor
        return True

    def shift_up_to(self, price: Decimal) -> None:
        """价格冲破上沿后整窗上移，重建基准阶梯（延伸清零）。"""
        self._lower, self._upper = shift_window_up(
            self._lower,
            self._upper,
            self._config.grid_count,
            self._config.spacing_mode,
            price,
            self._config.price_tick,
        )
        self._build_base()
