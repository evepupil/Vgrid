"""定投回测引擎：把 BarSeries 跑成 DcaResult（纯逻辑，不碰 I/O）。

流程：
1. 按频率排日程 → 映射到 K 线下标（``schedule``）。
2. 逐根 K 线走：到投入日就按金额规则算「想投多少」→ 受「剩余上限 / 现金」约束 → 按手取整
   → 扣银河费买入（买不满一手 / 触顶 / 现金不足则跳过并记原因）。每根收盘记一笔权益。
3. 汇总指标（含 XIRR）。

成交口径：一律在执行 K 线的 ``open`` 成交；金额信号只用该 K 线**之前**的收盘（无未来函数）。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from vgrid.backtest.metrics import max_drawdown_of
from vgrid.backtest.result import EquityPoint
from vgrid.core.bar import BarSeries
from vgrid.core.money import shares_for_amount
from vgrid.dca.amount import amount_for
from vgrid.dca.config import DcaConfig
from vgrid.dca.result import DcaMetrics, DcaResult, DcaTrade, SkippedBuy
from vgrid.dca.schedule import map_to_bars, scheduled_dates
from vgrid.dca.xirr import xirr


def run_dca(config: DcaConfig, bars: BarSeries) -> DcaResult:
    """对 ``bars`` 跑定投回测，返回成交、逐 K 权益曲线、绩效指标。"""
    if not bars.bars:
        raise ValueError("至少需要一根 K 线才能回测")

    all_bars = bars.bars
    buy_days = set(
        map_to_bars(
            scheduled_dates(
                config.frequency,
                all_bars[0].ts.date(),
                all_bars[-1].ts.date(),
                weekday=config.weekday,
                day_of_month=config.day_of_month,
            ),
            all_bars,
        )
    )

    cash = config.start_cash
    shares = 0
    invested = Decimal(0)  # 累计成交额（本金口径）
    total_fee = Decimal(0)
    trades: list[DcaTrade] = []
    skipped: list[SkippedBuy] = []
    equity_curve: list[EquityPoint] = []
    prior_closes: list[Decimal] = []

    for idx, bar in enumerate(all_bars):
        if idx in buy_days:
            outcome = _try_buy(config, bar.ts, bar.open, prior_closes, cash, invested)
            if isinstance(outcome, DcaTrade):
                cash -= outcome.cash_out
                shares += outcome.shares
                invested += outcome.notional
                total_fee += outcome.fee
                trades.append(outcome)
            else:
                skipped.append(SkippedBuy(ts=bar.ts, reason=outcome))
        pos_value = Decimal(shares) * bar.close
        equity_curve.append(
            EquityPoint(ts=bar.ts, cash=cash, position_value=pos_value, equity=cash + pos_value)
        )
        prior_closes.append(bar.close)

    metrics = _metrics(
        config, tuple(trades), tuple(equity_curve), bars, invested, total_fee, len(skipped)
    )
    return DcaResult(
        trades=tuple(trades),
        equity_curve=tuple(equity_curve),
        bars=all_bars,
        metrics=metrics,
        skipped=tuple(skipped),
    )


def _try_buy(
    config: DcaConfig,
    ts: datetime,
    price: Decimal,
    prior_closes: list[Decimal],
    cash: Decimal,
    invested: Decimal,
) -> DcaTrade | str:
    """算本次买入；成功返回 DcaTrade，否则返回跳过原因字符串。"""
    desired = amount_for(config.amount_policy, config.base_amount, prior_closes, price)
    remaining_cap = config.cash_cap - invested
    if remaining_cap <= 0:
        return "已达累计投入上限"
    budget = min(desired, remaining_cap, cash)
    if budget <= 0:
        return "现金不足"
    shares = shares_for_amount(budget, price, config.lot_size)
    if shares <= 0:
        return "买不满一手"
    notional = price * shares
    fee = config.fee.compute(notional)
    if notional + fee > cash:  # 含手续费后现金不够，退一手再试
        shares -= config.lot_size
        if shares <= 0:
            return "现金不足"
        notional = price * shares
        fee = config.fee.compute(notional)
    multiplier = desired / config.base_amount if config.base_amount else Decimal(1)
    return DcaTrade(
        ts=ts, price=price, shares=shares, notional=notional, fee=fee, multiplier=multiplier
    )


def _metrics(
    config: DcaConfig,
    trades: tuple[DcaTrade, ...],
    equity_curve: tuple[EquityPoint, ...],
    bars: BarSeries,
    invested: Decimal,
    total_fee: Decimal,
    skipped_count: int,
) -> DcaMetrics:
    initial_cash = config.start_cash
    final_cash = equity_curve[-1].cash
    final_market_value = equity_curve[-1].position_value
    final_equity = equity_curve[-1].equity
    profit_on_invested = final_market_value - invested
    return DcaMetrics(
        initial_cash=initial_cash,
        invested_amount=invested,
        final_cash=final_cash,
        final_market_value=final_market_value,
        final_equity=final_equity,
        profit=final_equity - initial_cash,
        profit_on_invested=profit_on_invested,
        profit_rate_on_invested=(profit_on_invested / invested) if invested > 0 else Decimal(0),
        xirr=_xirr_of(trades, final_market_value, bars),
        max_drawdown=max_drawdown_of(equity_curve),
        total_fee=total_fee,
        n_buys=len(trades),
        skipped_count=skipped_count,
        buy_hold_return=_buy_hold(config, bars),
    )


def _xirr_of(trades: tuple[DcaTrade, ...], final_value: Decimal, bars: BarSeries) -> Decimal | None:
    """现金流 = 各笔买入流出（负）+ 期末持仓清仓流入（正），解年化。"""
    if not trades:
        return None
    flows = [(t.ts.date(), -t.cash_out) for t in trades]
    flows.append((bars.bars[-1].ts.date(), final_value))
    return xirr(flows)


def _buy_hold(config: DcaConfig, bars: BarSeries) -> Decimal:
    """同笔起始现金首根开盘买满、持有到末根收盘卖出（扣两边费）的收益率（对照）。"""
    initial_cash = config.start_cash
    entry = bars.bars[0].open
    shares = shares_for_amount(initial_cash, entry, config.lot_size)
    if shares <= 0 or initial_cash <= 0:
        return Decimal(0)
    buy_notional = entry * shares
    cost = buy_notional + config.fee.compute(buy_notional)
    exit_notional = bars.bars[-1].close * shares
    proceeds = exit_notional - config.fee.compute(exit_notional)
    return (proceeds - cost) / initial_cash
