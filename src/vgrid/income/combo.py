"""红利增强组合回测：把「分红再投」叠加到任意策略（定投 / 网格）之上。

策略在**不复权**价上跑（除权日价格真跌、分红是补偿）。本模块从策略的逐 bar 权益曲线
反推每根持仓份额（``position_value / close``），按持仓在发放日收分红、下一交易日开盘再投，
量化分红给策略额外加的收益——**不改动 DCA / 网格引擎**，只在其权益曲线上叠一个「分红再投桶」。

分红口径「再投」：策略持仓 + 分红桶持仓都享分红，现金下一根开盘买回（扣费、买不满一手留现金）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from vgrid.backtest.matcher import simulate
from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.fees import FeeModel
from vgrid.dca.config import DcaConfig
from vgrid.dca.engine import run_dca
from vgrid.income.models import DividendEvent
from vgrid.income.series import SeriesPoint, _pay_bar_index


@dataclass(frozen=True, slots=True)
class ComboResult:
    """策略「价格口径」vs「分红再投增强」的对照结果。"""

    strategy_return: Decimal  # 价格口径末收益（不含分红，除权日跌价没补回）
    enhanced_return: Decimal  # 分红再投增强末收益
    dividend_boost: Decimal  # 分红贡献 = enhanced − strategy
    strategy_curve: list[SeriesPoint]  # 归一到 initial_cash 的策略收益曲线
    enhanced_curve: list[SeriesPoint]
    dividend_cash_total: Decimal  # 期间累计到账分红现金
    reinvest_shares: int  # 分红再投累计买入份额


def _shares_held(point: EquityPoint, close: Decimal) -> int:
    """从逐 bar 权益反推策略当根持仓份额（position_value = 份额 × 收盘）。"""
    if close <= 0:
        return 0
    return round(point.position_value / close)


def dividend_reinvest_overlay(
    bars: Sequence[Bar],
    dividends: Sequence[DividendEvent],
    equity_curve: Sequence[EquityPoint],
    *,
    initial_cash: Decimal,
    lot_size: int,
    fee: FeeModel,
) -> ComboResult:
    """在策略逐 bar 权益曲线上叠加分红再投，返回价格口径 / 增强两条曲线与分红贡献。"""
    if not bars:
        raise ValueError("无 bar，无法叠加分红")
    if len(equity_curve) != len(bars):
        raise ValueError(f"权益曲线与 bar 数不一致：{len(equity_curve)} vs {len(bars)}")

    pays: dict[int, list[Decimal]] = {}
    for ev in dividends:
        idx = _pay_bar_index(bars, ev)
        if idx is not None:
            pays.setdefault(idx, []).append(ev.per_share)

    bucket_shares = 0
    bucket_cash = Decimal(0)
    pending = Decimal(0)  # 已到账、待下一根开盘买入的分红现金
    dividend_cash_total = Decimal(0)
    strategy_curve: list[SeriesPoint] = []
    enhanced_curve: list[SeriesPoint] = []

    for i, bar in enumerate(bars):
        # 1) 上一根到账的分红按本根开盘买回，买不满一手转现金。
        if pending > 0:
            new = int((pending / bar.open) // lot_size) * lot_size
            if new > 0:
                notional = new * bar.open
                cost = notional + fee.compute(notional)
                if cost <= pending:
                    bucket_shares += new
                    pending -= cost
            bucket_cash += pending
            pending = Decimal(0)
        # 2) 本根发放日：策略持仓 + 分红桶持仓都享分红。
        held = _shares_held(equity_curve[i], bar.close)
        for per_share in pays.get(i, []):
            cash = (held + bucket_shares) * per_share
            pending += cash
            dividend_cash_total += cash
        # 3) 快照：增强 = 策略权益 + 分红桶（持仓市值 + 现金 + 待投）。
        strat_equity = equity_curve[i].equity
        bucket_equity = bucket_shares * bar.close + bucket_cash + pending
        day = bar.ts.date()
        strategy_curve.append(SeriesPoint(day, strat_equity / initial_cash - 1))
        enhanced_curve.append(SeriesPoint(day, (strat_equity + bucket_equity) / initial_cash - 1))

    strategy_return = strategy_curve[-1].value
    enhanced_return = enhanced_curve[-1].value
    return ComboResult(
        strategy_return=strategy_return,
        enhanced_return=enhanced_return,
        dividend_boost=enhanced_return - strategy_return,
        strategy_curve=strategy_curve,
        enhanced_curve=enhanced_curve,
        dividend_cash_total=dividend_cash_total,
        reinvest_shares=bucket_shares,
    )


def dca_dividend_combo(
    config: DcaConfig,
    bars: BarSeries,
    dividends: Sequence[DividendEvent],
) -> ComboResult:
    """定投 + 分红再投：run_dca 跑基准，再叠分红桶。bars 应为不复权价。"""
    result = run_dca(config, bars)
    return dividend_reinvest_overlay(
        bars.bars,
        dividends,
        result.equity_curve,
        initial_cash=config.start_cash,
        lot_size=config.lot_size,
        fee=config.fee,
    )


def grid_dividend_combo(
    config: GridConfig,
    bars: BarSeries,
    dividends: Sequence[DividendEvent],
    *,
    initial_cash: Decimal | None = None,
) -> ComboResult:
    """网格 + 分红再投：simulate 跑基准，再叠分红桶。bars 应为不复权价。"""
    initial = initial_cash if initial_cash is not None else config.capital_cap
    result = simulate(config, bars, initial_cash=initial)
    return dividend_reinvest_overlay(
        bars.bars,
        dividends,
        result.equity_curve,
        initial_cash=initial,
        lot_size=config.lot_size,
        fee=config.fee,
    )
