"""网格策略配置。

一个 ``GridConfig`` 完整描述一条网格策略的全部参数，回测 / 模拟盘 / 实盘共用。
所有会被参数扫描（M3）调优的旋钮都集中在这里。
"""

from dataclasses import dataclass, field
from decimal import Decimal

from vgrid.core.enums import BaseBuildMode, SpacingMode
from vgrid.core.fees import FeeModel
from vgrid.core.money import LOT_SIZE, PRICE_TICK


@dataclass(frozen=True, slots=True)
class GridConfig:
    """网格策略参数。

    Attributes:
        symbol: 标的代码，如 "159920"（恒生 ETF）。
        lower_price: 初始网格区间下沿。
        upper_price: 初始网格区间上沿。
        grid_count: 初始区间内的格数（→ grid_count + 1 条网格线）。
        per_grid_amount: 每格买入金额（元）。建议 ≥ 2000，否则费率被保底费拉高。
        capital_cap: 占用资金硬上限（元），达到就停止新买单，兜底黑天鹅。
        spacing_mode: 等差 / 等比。
        base_build_mode: 中枢建仓 / 零底仓。
        upper_rebuild_ratio: 向上突破后底仓重建比例 [0,1]。
            0 = 只挂买单等回调再买（不追高）；1 = 立即按市价重建；中间按比例。
        down_spacing_factor: 向下突破后每延伸一格，格距乘的系数（≥1，越跌格子越宽）。
        down_amount_factor: 向下突破后每延伸一格，每格金额乘的系数（>0）。
        fee: 手续费模型。
        lot_size: 一手份额，默认 100。
        price_tick: 价格最小变动单位，默认 0.001。
    """

    symbol: str
    lower_price: Decimal
    upper_price: Decimal
    grid_count: int
    per_grid_amount: Decimal
    capital_cap: Decimal
    spacing_mode: SpacingMode = SpacingMode.ARITHMETIC
    base_build_mode: BaseBuildMode = BaseBuildMode.CENTER
    upper_rebuild_ratio: Decimal = Decimal("0")
    down_spacing_factor: Decimal = Decimal("1")
    down_amount_factor: Decimal = Decimal("1")
    fee: FeeModel = field(default_factory=FeeModel)
    lot_size: int = LOT_SIZE
    price_tick: Decimal = PRICE_TICK

    def __post_init__(self) -> None:
        if self.lower_price <= 0:
            raise ValueError(f"下沿价格必须为正：{self.lower_price}")
        if self.upper_price <= self.lower_price:
            raise ValueError(
                f"上沿价格 {self.upper_price} 必须大于下沿 {self.lower_price}"
            )
        if self.grid_count < 1:
            raise ValueError(f"格数至少为 1：{self.grid_count}")
        if self.per_grid_amount <= 0:
            raise ValueError(f"每格金额必须为正：{self.per_grid_amount}")
        if self.capital_cap <= 0:
            raise ValueError(f"资金上限必须为正：{self.capital_cap}")
        if not (Decimal(0) <= self.upper_rebuild_ratio <= Decimal(1)):
            raise ValueError(
                f"库存重建比例必须在 [0,1]：{self.upper_rebuild_ratio}"
            )
        if self.down_spacing_factor < 1:
            raise ValueError(
                f"向下格距放大系数必须 ≥ 1：{self.down_spacing_factor}"
            )
        if self.down_amount_factor <= 0:
            raise ValueError(
                f"向下金额系数必须为正：{self.down_amount_factor}"
            )
        if self.lot_size < 1:
            raise ValueError(f"一手份额至少为 1：{self.lot_size}")
        if self.price_tick <= 0:
            raise ValueError(f"价格变动单位必须为正：{self.price_tick}")

    @property
    def is_amount_fee_efficient(self) -> bool:
        """每格金额是否达到「费率不被保底费拉高」的临界值。"""
        return self.per_grid_amount >= self.fee.min_efficient_notional
