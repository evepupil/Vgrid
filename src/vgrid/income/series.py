"""四条收益曲线（纯函数，离线可测）。

同一只红利 ETF 用四种口径各算一条「起点归零的累计收益率」序列，直接可比、可画：

1. 价格：只看未复权收盘价涨跌。
2. 价格 + 现金分红：分红发放日到账留现金、份额不变。
3. 价格 + 分红再投：发放日收现金，下一交易日开盘买回（扣银河费、买不满一手留现金）。
4. 累计净值：直接用基金累计净值，作校验基准。

份额取整用 ``lot_size``、再投扣费用 ``FeeModel``，和网格 / 定投同口径。再投严格「发放日
收钱、次日开盘买」，不看未来。所有曲线以 ``initial_cash`` 满仓建仓为基准，起点收益率恒为 0。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from vgrid.core.bar import Bar
from vgrid.core.fees import FeeModel
from vgrid.income.models import DividendEvent, NavPoint


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    """曲线上一点：某日的累计收益率（起点=0）。"""

    day: date
    value: Decimal


def _initial_shares(initial_cash: Decimal, first_close: Decimal, lot_size: int) -> int:
    """起始满仓：按 ``initial_cash`` 在首日收盘价能买的整手份额。"""
    shares = int((initial_cash / first_close) // lot_size) * lot_size
    if shares <= 0:
        raise ValueError(
            f"起始现金 {initial_cash} 在首价 {first_close} 下买不满一手（lot={lot_size}），"
            "调大 initial_cash 或调小 lot_size",
        )
    return shares


def _first_bar_on_or_after(bars: Sequence[Bar], day: date) -> int | None:
    """返回首个日期 ≥ ``day`` 的 bar 下标；``day`` 晚于全部 bar 返回 None。"""
    for i, bar in enumerate(bars):
        if bar.ts.date() >= day:
            return i
    return None


def _pay_bar_index(bars: Sequence[Bar], ev: DividendEvent) -> int | None:
    """分红发放日落在样本内的哪根 bar；落在样本区间外（早于首日 / 晚于末日）返回 None。"""
    if not bars or ev.pay_date < bars[0].ts.date():
        return None
    return _first_bar_on_or_after(bars, ev.pay_date)


def price_curve(bars: Sequence[Bar]) -> list[SeriesPoint]:
    """价格曲线：未复权收盘价相对首日涨跌。"""
    if not bars:
        return []
    first = bars[0].close
    return [SeriesPoint(b.ts.date(), b.close / first - 1) for b in bars]


def acc_nav_curve(navs: Sequence[NavPoint]) -> list[SeriesPoint]:
    """累计净值曲线：累计净值相对首日涨跌（校验基准）。"""
    if not navs:
        return []
    first = navs[0].acc_nav
    return [SeriesPoint(n.day, n.acc_nav / first - 1) for n in navs]


def cash_dividend_curve(
    bars: Sequence[Bar],
    dividends: Sequence[DividendEvent],
    *,
    initial_cash: Decimal,
    lot_size: int,
) -> list[SeriesPoint]:
    """价格 + 现金分红：份额不变，分红发放日到账后留作现金、不再买入。"""
    if not bars:
        return []
    shares = _initial_shares(initial_cash, bars[0].close, lot_size)
    cash0 = initial_cash - shares * bars[0].close

    # 每根 bar 当日到账的现金分红（每份分红 × 恒定份额）。
    received = [Decimal(0)] * len(bars)
    for ev in dividends:
        idx = _pay_bar_index(bars, ev)
        if idx is not None:
            received[idx] += shares * ev.per_share

    points: list[SeriesPoint] = []
    cash = cash0
    for i, bar in enumerate(bars):
        cash += received[i]
        equity = shares * bar.close + cash
        points.append(SeriesPoint(bar.ts.date(), equity / initial_cash - 1))
    return points


def reinvest_curve(
    bars: Sequence[Bar],
    dividends: Sequence[DividendEvent],
    *,
    initial_cash: Decimal,
    lot_size: int,
    fee: FeeModel,
) -> list[SeriesPoint]:
    """价格 + 分红再投：发放日收现金，下一交易日开盘买回（扣费、买不满一手留现金）。"""
    if not bars:
        return []
    shares = _initial_shares(initial_cash, bars[0].close, lot_size)
    cash = initial_cash - shares * bars[0].close

    # 每根 bar 当日到账的每份分红（份额随再投增长，故按 bar 逐笔处理、不预乘份额）。
    pays: dict[int, list[Decimal]] = {}
    for ev in dividends:
        idx = _pay_bar_index(bars, ev)
        if idx is not None:
            pays.setdefault(idx, []).append(ev.per_share)

    points: list[SeriesPoint] = []
    pending = Decimal(0)  # 已到账、待下一根开盘买入的现金
    for i, bar in enumerate(bars):
        # 1) 把上一根到账的现金按本根开盘价买回，买不满一手的留作现金。
        if pending > 0:
            new = int((pending / bar.open) // lot_size) * lot_size
            if new > 0:
                notional = new * bar.open
                cost = notional + fee.compute(notional)
                if cost <= pending:
                    shares += new
                    pending -= cost
            cash += pending
            pending = Decimal(0)
        # 2) 本根发放日到账现金（下一根再投）。
        for per_share in pays.get(i, []):
            pending += shares * per_share
        # 3) 收盘快照：待投现金也算现金。
        equity = shares * bar.close + cash + pending
        points.append(SeriesPoint(bar.ts.date(), equity / initial_cash - 1))
    return points
