"""量化定投（DCA）配置。

一个 ``DcaConfig`` 完整描述一条定投策略：多久投一次（日程）、每次投多少（金额规则）、
投到多少封顶。金额规则三选一：固定金额、跌幅加码、均线偏离。所有金额 / 价格用
``Decimal``，份额取整和手续费复用 core 的同一套（和网格口径一致，便于对比）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from vgrid.core.fees import FeeModel
from vgrid.core.money import LOT_SIZE, PRICE_TICK

_ISO_SUNDAY = 7  # ISO 星期上界（1=周一…7=周日）
_MAX_DAY_OF_MONTH = 31  # 号数上界（超当月天数在排程时钳到月末）


class Frequency(StrEnum):
    """定投频率。

    - DAILY：每个交易日投一次。
    - WEEKLY：每周固定星期几（``weekday`` ISO 1=周一…7=周日）。
    - MONTHLY：每月固定某日（``day_of_month``，超过当月天数钳到月末）。
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AmountMode(StrEnum):
    """每次买多少的规则。

    - FIXED：固定 ``base_amount``，雷打不动，是所有增强规则的对照基准。
    - DRAWDOWN：跌幅加码，从近期高点回撤越多、买越多（按档位放大）。
    - MA_DEVIATION：均线偏离，价格低于均线多买、高于均线少买（便宜多买贵少买）。
    """

    FIXED = "fixed"
    DRAWDOWN = "drawdown"
    MA_DEVIATION = "ma_deviation"


@dataclass(frozen=True, slots=True)
class DrawdownTier:
    """跌幅加码的一档：回撤达到 ``drawdown`` 时，投入乘 ``multiplier``。"""

    drawdown: Decimal  # 回撤阈值（0~1，如 0.10 = 回撤 10%）
    multiplier: Decimal  # 金额倍数（如 1.5）

    def __post_init__(self) -> None:
        if not (Decimal(0) < self.drawdown <= Decimal(1)):
            raise ValueError(f"回撤阈值必须在 (0,1]：{self.drawdown}")
        if self.multiplier <= 0:
            raise ValueError(f"金额倍数必须为正：{self.multiplier}")


@dataclass(frozen=True, slots=True)
class AmountPolicy:
    """金额规则（按 ``mode`` 取不同字段）。

    - FIXED：无额外字段。
    - DRAWDOWN：``lookback_days``（回看多少根 K 线找高点）+ ``tiers``（档位，按回撤升序）。
    - MA_DEVIATION：``ma_window`` + 低于 / 持平 / 高于均线的三个倍数。
    """

    mode: AmountMode = AmountMode.FIXED
    # DRAWDOWN
    lookback_days: int = 120
    tiers: tuple[DrawdownTier, ...] = ()
    # MA_DEVIATION
    ma_window: int = 60
    below_multiplier: Decimal = Decimal("1.5")
    normal_multiplier: Decimal = Decimal("1")
    above_multiplier: Decimal = Decimal("0.5")

    def __post_init__(self) -> None:
        if self.mode is AmountMode.DRAWDOWN:
            if self.lookback_days < 1:
                raise ValueError(f"回看根数至少为 1：{self.lookback_days}")
            if not self.tiers:
                raise ValueError("跌幅加码至少要有一档 tier")
        if self.mode is AmountMode.MA_DEVIATION:
            if self.ma_window < 1:
                raise ValueError(f"均线窗口至少为 1：{self.ma_window}")
            for name, mult in (
                ("below", self.below_multiplier),
                ("normal", self.normal_multiplier),
                ("above", self.above_multiplier),
            ):
                if mult < 0:
                    raise ValueError(f"{name} 倍数不能为负：{mult}")

    @property
    def sorted_tiers(self) -> tuple[DrawdownTier, ...]:
        """按回撤阈值升序的档位（取「满足的最高档」时用）。"""
        return tuple(sorted(self.tiers, key=lambda t: t.drawdown))


@dataclass(frozen=True, slots=True)
class DcaConfig:
    """定投策略参数。

    Attributes:
        symbol: 标的代码。
        frequency: 定投频率。
        base_amount: 每次基准投入金额（元）。建议 ≥ 2000，否则费率被保底费拉高。
        cash_cap: 累计投入上限（元），累计成交额达到就停止买入，防回测里无限加钱。
        weekday: WEEKLY 时的星期（ISO 1=周一…7=周日）。
        day_of_month: MONTHLY 时的号数（1~31，超月末钳到月末）。
        amount_policy: 金额规则。
        initial_cash: 账户初始现金，默认等于 ``cash_cap``（把预算一次备足）。
        fee: 手续费模型（同网格）。
        lot_size / price_tick: 一手份额 / 价格最小变动，默认同全局。
    """

    symbol: str
    frequency: Frequency
    base_amount: Decimal
    cash_cap: Decimal
    weekday: int = 1
    day_of_month: int = 1
    amount_policy: AmountPolicy = field(default_factory=AmountPolicy)
    initial_cash: Decimal | None = None
    fee: FeeModel = field(default_factory=FeeModel)
    lot_size: int = LOT_SIZE
    price_tick: Decimal = PRICE_TICK

    def __post_init__(self) -> None:
        if self.base_amount <= 0:
            raise ValueError(f"每次投入必须为正：{self.base_amount}")
        if self.cash_cap <= 0:
            raise ValueError(f"累计投入上限必须为正：{self.cash_cap}")
        if not (1 <= self.weekday <= _ISO_SUNDAY):
            raise ValueError(f"weekday 必须在 1~7（ISO）：{self.weekday}")
        if not (1 <= self.day_of_month <= _MAX_DAY_OF_MONTH):
            raise ValueError(f"day_of_month 必须在 1~31：{self.day_of_month}")
        if self.initial_cash is not None and self.initial_cash <= 0:
            raise ValueError(f"初始现金必须为正：{self.initial_cash}")
        if self.lot_size < 1:
            raise ValueError(f"一手份额至少为 1：{self.lot_size}")
        if self.price_tick <= 0:
            raise ValueError(f"价格变动单位必须为正：{self.price_tick}")

    @property
    def start_cash(self) -> Decimal:
        """账户实际起始现金（未显式给则用 cash_cap）。"""
        return self.initial_cash if self.initial_cash is not None else self.cash_cap

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化 dict（``Decimal`` 转 str 保精度）。"""
        policy = self.amount_policy
        policy_dict: dict[str, Any] = {"mode": policy.mode.value}
        if policy.mode is AmountMode.DRAWDOWN:
            policy_dict["lookback_days"] = policy.lookback_days
            policy_dict["tiers"] = [
                {"drawdown": str(t.drawdown), "multiplier": str(t.multiplier)} for t in policy.tiers
            ]
        elif policy.mode is AmountMode.MA_DEVIATION:
            policy_dict["ma_window"] = policy.ma_window
            policy_dict["below_multiplier"] = str(policy.below_multiplier)
            policy_dict["normal_multiplier"] = str(policy.normal_multiplier)
            policy_dict["above_multiplier"] = str(policy.above_multiplier)
        out: dict[str, Any] = {
            "type": "dca",
            "symbol": self.symbol,
            "frequency": self.frequency.value,
            "base_amount": str(self.base_amount),
            "cash_cap": str(self.cash_cap),
            "weekday": self.weekday,
            "day_of_month": self.day_of_month,
            "amount_policy": policy_dict,
            "fee": {"rate": str(self.fee.rate), "min_fee": str(self.fee.min_fee)},
            "lot_size": self.lot_size,
            "price_tick": str(self.price_tick),
        }
        if self.initial_cash is not None:
            out["initial_cash"] = str(self.initial_cash)
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DcaConfig:
        """从 dict 反序列化（``to_dict`` 的逆操作），供 CLI ``--config`` 用。"""
        fee_raw = data.get("fee")
        fee = (
            FeeModel(
                rate=Decimal(str(fee_raw["rate"])),
                min_fee=Decimal(str(fee_raw["min_fee"])),
            )
            if isinstance(fee_raw, Mapping)
            else FeeModel()
        )
        return cls(
            symbol=str(data["symbol"]),
            frequency=Frequency(data["frequency"]),
            base_amount=Decimal(str(data["base_amount"])),
            cash_cap=Decimal(str(data["cash_cap"])),
            weekday=int(data["weekday"]) if "weekday" in data else 1,
            day_of_month=int(data["day_of_month"]) if "day_of_month" in data else 1,
            amount_policy=_policy_from_dict(data.get("amount_policy")),
            initial_cash=Decimal(str(data["initial_cash"])) if "initial_cash" in data else None,
            fee=fee,
            lot_size=int(data["lot_size"]) if "lot_size" in data else LOT_SIZE,
            price_tick=Decimal(str(data["price_tick"])) if "price_tick" in data else PRICE_TICK,
        )


def _policy_from_dict(raw: object) -> AmountPolicy:
    """金额规则 dict → AmountPolicy（缺省为固定金额）。"""
    if not isinstance(raw, Mapping):
        return AmountPolicy()
    mode = AmountMode(raw.get("mode", AmountMode.FIXED.value))
    if mode is AmountMode.DRAWDOWN:
        tiers = tuple(
            DrawdownTier(
                drawdown=Decimal(str(t["drawdown"])),
                multiplier=Decimal(str(t["multiplier"])),
            )
            for t in raw.get("tiers", [])
        )
        return AmountPolicy(
            mode=mode,
            lookback_days=int(raw.get("lookback_days", 120)),
            tiers=tiers,
        )
    if mode is AmountMode.MA_DEVIATION:
        return AmountPolicy(
            mode=mode,
            ma_window=int(raw.get("ma_window", 60)),
            below_multiplier=Decimal(str(raw.get("below_multiplier", "1.5"))),
            normal_multiplier=Decimal(str(raw.get("normal_multiplier", "1"))),
            above_multiplier=Decimal(str(raw.get("above_multiplier", "0.5"))),
        )
    return AmountPolicy(mode=AmountMode.FIXED)
