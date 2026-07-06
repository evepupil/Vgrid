"""手续费模型。

银河证券超低 ETF 费率：``fee = max(0.1 元, 成交额 × 万0.5)``，ETF 免印花税。

「0.1 元起收」有个临界点：0.1 ÷ 0.00005 = 2000 元。单笔成交额 ≥ 2000 元时费率
才是实打实的万0.5，低于 2000 会被保底费拉高——所以每格金额建议不低于 2000 元。
"""

from dataclasses import dataclass
from decimal import Decimal

from vgrid.core.money import quantize_cash


@dataclass(frozen=True, slots=True)
class FeeModel:
    """成交手续费计算。

    Attributes:
        rate: 佣金费率，默认万0.5（0.00005）。
        min_fee: 单笔最低佣金，默认 0.1 元。
    """

    rate: Decimal = Decimal("0.00005")
    min_fee: Decimal = Decimal("0.1")

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError(f"费率不能为负：{self.rate}")
        if self.min_fee < 0:
            raise ValueError(f"最低佣金不能为负：{self.min_fee}")

    def compute(self, notional: Decimal) -> Decimal:
        """按成交额算手续费，结果对齐到分。"""
        if notional < 0:
            raise ValueError(f"成交额不能为负：{notional}")
        commission = quantize_cash(notional * self.rate)
        return max(self.min_fee, commission)

    @property
    def min_efficient_notional(self) -> Decimal:
        """费率不被保底费拉高的临界成交额（min_fee / rate）。

        单笔成交额低于这个值，实际费率就高于名义费率了。
        """
        if self.rate == 0:
            return Decimal(0)
        return self.min_fee / self.rate
