"""绩效统计纯函数。

从权益曲线 + 成交序列算收益率 / 年化 / 最大回撤 / 夏普 / 胜率 / 盈亏比 / 手续费 /
买入持有对照。金额与比率一律 ``Decimal``：年化用 ``(1+r)^(1/years)``（``ln/exp``），
夏普用 ``sqrt``，都走 Decimal 上下文，不在统计环节引入 float。
"""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

from vgrid.backtest.result import BacktestMetrics, EquityPoint
from vgrid.core.bar import Bar
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame, Side
from vgrid.core.models import Fill
from vgrid.core.money import shares_for_amount


def compute_metrics(
    equity_curve: tuple[EquityPoint, ...],
    fills: tuple[Fill, ...],
    bars: tuple[Bar, ...],
    *,
    initial_cash: Decimal,
    config: GridConfig,
    frame: Frame,
) -> BacktestMetrics:
    if not equity_curve:
        raise ValueError("权益曲线为空，无法计算指标")

    final_equity = equity_curve[-1].equity
    total_return = _ratio(final_equity - initial_cash, initial_cash)
    sell_pnls = _sell_pnls(fills)
    total_fee = sum((f.fee for f in fills), Decimal(0))
    n_buys = sum(1 for f in fills if f.side is Side.BUY)
    n_sells = sum(1 for f in fills if f.side is Side.SELL)

    return BacktestMetrics(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=_annualized(total_return, bars),
        max_drawdown=_max_drawdown(equity_curve),
        sharpe=_sharpe(equity_curve, frame),
        win_rate=_win_rate(sell_pnls),
        profit_loss_ratio=_profit_loss_ratio(sell_pnls),
        n_buys=n_buys,
        n_sells=n_sells,
        total_fee=total_fee,
        buy_hold_return=_buy_hold(bars, initial_cash, config),
    )


# ------------------------------------------------------------------ 子计算


def _ratio(numer: Decimal, denom: Decimal) -> Decimal:
    if denom == 0:
        return Decimal(0)
    return numer / denom


_MIN_SAMPLES = 2  # 算年化 / 夏普所需的最少权益点数


def _annualized(total_return: Decimal, bars: tuple[Bar, ...]) -> Decimal:
    if len(bars) < _MIN_SAMPLES:
        return total_return
    days = Decimal(max((bars[-1].ts - bars[0].ts).days, 1))
    if days <= 0 or total_return <= -1:
        return total_return
    years = days / Decimal(365)
    # (1 + r)^(1/years) - 1，用 ln/exp 求 Decimal 幂
    base = (Decimal(1) + total_return).ln() / years
    return base.exp() - Decimal(1)


def _max_drawdown(equity_curve: tuple[EquityPoint, ...]) -> Decimal:
    peak = equity_curve[0].equity
    max_dd = Decimal(0)
    for pt in equity_curve:
        peak = max(peak, pt.equity)
        if peak > 0:
            dd = (peak - pt.equity) / peak
            max_dd = max(max_dd, dd)
    return max_dd


def _sharpe(equity_curve: tuple[EquityPoint, ...], frame: Frame) -> Decimal:
    if len(equity_curve) < _MIN_SAMPLES:
        return Decimal(0)
    returns: list[Decimal] = []
    for prev, cur in pairwise(equity_curve):
        if prev.equity > 0:
            returns.append(cur.equity / prev.equity - Decimal(1))
    if not returns:
        return Decimal(0)
    n = Decimal(len(returns))
    mean = sum(returns, Decimal(0)) / n
    var = sum((r - mean) ** 2 for r in returns) / n
    std = var.sqrt()
    if std == 0:
        return Decimal(0)
    annual_factor = Decimal(_periods_per_year(frame)).sqrt()
    return mean / std * annual_factor


def _periods_per_year(frame: Frame) -> int:
    """A 股：日线 252 个交易日；1 分钟线约 252 × 240 根。"""
    if frame is Frame.MINUTE:
        return 252 * 240
    return 252


def _sell_pnls(fills: tuple[Fill, ...]) -> list[Decimal]:
    pnls: list[Decimal] = []
    for f in fills:
        if f.side is Side.SELL and f.realized_pnl is not None:
            pnls.append(f.realized_pnl)
    return pnls


def _win_rate(sell_pnls: list[Decimal]) -> Decimal:
    if not sell_pnls:
        return Decimal(0)
    wins = sum(1 for p in sell_pnls if p > 0)
    return Decimal(wins) / Decimal(len(sell_pnls))


def _profit_loss_ratio(sell_pnls: list[Decimal]) -> Decimal:
    gains = [p for p in sell_pnls if p > 0]
    losses = [-p for p in sell_pnls if p < 0]  # 亏损额取正
    if not gains or not losses:
        return Decimal(0)
    avg_gain = sum(gains, Decimal(0)) / Decimal(len(gains))
    avg_loss = sum(losses, Decimal(0)) / Decimal(len(losses))
    if avg_loss == 0:
        return Decimal(0)
    return avg_gain / avg_loss


def _buy_hold(bars: tuple[Bar, ...], initial_cash: Decimal, config: GridConfig) -> Decimal:
    """同笔资金在首根开盘按手取整买入、持有到末根收盘卖出（扣两边手续费）的收益率。"""
    if not bars or initial_cash <= 0:
        return Decimal(0)
    entry = bars[0].open
    shares = shares_for_amount(initial_cash, entry, config.lot_size)
    if shares <= 0:
        return Decimal(0)
    buy_notional = entry * shares
    cost = buy_notional + config.fee.compute(buy_notional)
    exit_notional = bars[-1].close * shares
    proceeds = exit_notional - config.fee.compute(exit_notional)
    return _ratio(proceeds - cost, cost)
