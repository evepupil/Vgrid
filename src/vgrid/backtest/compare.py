"""策略对比：网格 / 定投 / 买入持有，同区间、同起始现金公平比较。

难点在口径统一：网格一上来就用满整笔资金，定投是逐步投入，两者的「收益率」分母不同。为了
回答最朴素的问题——「同样一笔钱、同一段行情，谁最后更有钱」——三者都用同一笔
``initial_cash`` 起步，比末权益 / 净利 / 对起始现金的收益率 / 自然日年化。定投额外给「实际
投入 + XIRR」作补充（它的钱是分批进场的，单看对起始现金的收益率会低估它的资金效率）。

纯逻辑，可单测。渲染交给 ``report.compare``。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from vgrid.backtest.matcher import simulate
from vgrid.backtest.metrics import annualized_return, max_drawdown_of
from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.fees import FeeModel
from vgrid.core.money import LOT_SIZE, shares_for_amount
from vgrid.dca.config import DcaConfig
from vgrid.dca.engine import run_dca


@dataclass(frozen=True, slots=True)
class StrategyRow:
    """对比表里的一行（一个策略）。

    ``total_return`` 一律对 ``initial_cash`` 算（同一笔起始现金的口径）。``invested`` / ``xirr``
    只有定投才有（分批投入的实际本金与真实年化），其余策略为 None。
    """

    name: str
    final_equity: Decimal
    profit: Decimal
    total_return: Decimal
    annualized_return: Decimal
    max_drawdown: Decimal
    total_fee: Decimal
    n_trades: int
    invested: Decimal | None = None
    xirr: Decimal | None = None
    curve: tuple[EquityPoint, ...] = ()  # 逐 K 权益，供 Web 叠加净值曲线（报告层不用）


@dataclass(frozen=True, slots=True)
class StrategyComparison:
    """一次三方对比的结果。"""

    initial_cash: Decimal
    bars: tuple[Bar, ...]
    rows: tuple[StrategyRow, ...]


def compare_strategies(
    bars: BarSeries,
    *,
    initial_cash: Decimal,
    grid_config: GridConfig | None = None,
    dca_config: DcaConfig | None = None,
) -> StrategyComparison:
    """跑齐给定策略 + 买入持有基线，返回同口径对比。至少给一个策略配置。"""
    if not bars.bars:
        raise ValueError("至少需要一根 K 线才能对比")
    if grid_config is None and dca_config is None:
        raise ValueError("至少要给网格或定投配置之一")
    if initial_cash <= 0:
        raise ValueError(f"起始现金必须为正：{initial_cash}")

    fee, lot_size = _fee_and_lot(grid_config, dca_config)
    rows: list[StrategyRow] = []
    if grid_config is not None:
        rows.append(_grid_row(grid_config, bars, initial_cash))
    if dca_config is not None:
        rows.append(_dca_row(dca_config, bars, initial_cash))
    rows.append(_buy_hold_row(bars, initial_cash, fee, lot_size))
    return StrategyComparison(initial_cash=initial_cash, bars=bars.bars, rows=tuple(rows))


def _fee_and_lot(
    grid_config: GridConfig | None, dca_config: DcaConfig | None
) -> tuple[FeeModel, int]:
    """买入持有基线用哪套费率 / 手数：优先跟网格，其次定投，都没有就默认。"""
    if grid_config is not None:
        return grid_config.fee, grid_config.lot_size
    if dca_config is not None:
        return dca_config.fee, dca_config.lot_size
    return FeeModel(), LOT_SIZE


def _grid_row(config: GridConfig, bars: BarSeries, initial_cash: Decimal) -> StrategyRow:
    result = simulate(config, bars, initial_cash=initial_cash)
    m = result.metrics
    return StrategyRow(
        name="网格",
        final_equity=m.final_equity,
        profit=m.final_equity - initial_cash,
        total_return=m.total_return,
        annualized_return=m.annualized_return,
        max_drawdown=m.max_drawdown,
        total_fee=m.total_fee,
        n_trades=m.n_buys + m.n_sells,
        curve=result.equity_curve,
    )


def _dca_row(config: DcaConfig, bars: BarSeries, initial_cash: Decimal) -> StrategyRow:
    # 用同一笔起始现金，定投自己的 cash_cap 决定实际投入多少
    result = run_dca(replace(config, initial_cash=initial_cash), bars)
    m = result.metrics
    total_return = (m.final_equity - initial_cash) / initial_cash
    return StrategyRow(
        name="定投",
        final_equity=m.final_equity,
        profit=m.profit,
        total_return=total_return,
        annualized_return=annualized_return(total_return, bars.bars),
        max_drawdown=m.max_drawdown,
        total_fee=m.total_fee,
        n_trades=m.n_buys,
        invested=m.invested_amount,
        xirr=m.xirr,
        curve=result.equity_curve,
    )


def _buy_hold_row(
    bars: BarSeries, initial_cash: Decimal, fee: FeeModel, lot_size: int
) -> StrategyRow:
    """首根开盘按手买满、持有到末根（持仓按收盘估值，和网格 / 定投同口径不强制卖出）。"""
    entry = bars.bars[0].open
    shares = shares_for_amount(initial_cash, entry, lot_size)
    if shares <= 0:  # 买不满一手，全程空仓
        flat = tuple(
            EquityPoint(ts=b.ts, cash=initial_cash, position_value=Decimal(0), equity=initial_cash)
            for b in bars.bars
        )
        return StrategyRow(
            name="买入持有",
            final_equity=initial_cash,
            profit=Decimal(0),
            total_return=Decimal(0),
            annualized_return=Decimal(0),
            max_drawdown=Decimal(0),
            total_fee=Decimal(0),
            n_trades=0,
            curve=flat,
        )
    buy_notional = entry * shares
    buy_fee = fee.compute(buy_notional)
    leftover = initial_cash - buy_notional - buy_fee
    curve = tuple(
        EquityPoint(
            ts=b.ts,
            cash=leftover,
            position_value=Decimal(shares) * b.close,
            equity=leftover + Decimal(shares) * b.close,
        )
        for b in bars.bars
    )
    final_equity = curve[-1].equity
    total_return = (final_equity - initial_cash) / initial_cash
    return StrategyRow(
        name="买入持有",
        final_equity=final_equity,
        profit=final_equity - initial_cash,
        total_return=total_return,
        annualized_return=annualized_return(total_return, bars.bars),
        max_drawdown=max_drawdown_of(curve),
        total_fee=buy_fee,
        n_trades=1,
        curve=curve,
    )
