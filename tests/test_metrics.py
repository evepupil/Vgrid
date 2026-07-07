"""绩效统计测试（手算案例）。"""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from vgrid.backtest.metrics import compute_metrics
from vgrid.backtest.result import EquityPoint
from vgrid.core import GridConfig
from vgrid.core.bar import Bar
from vgrid.core.enums import Frame, Side
from vgrid.core.models import Fill

MakeConfig = Callable[..., GridConfig]


def _eq(equity: str) -> EquityPoint:
    return EquityPoint(
        ts=datetime(2024, 1, 1),
        cash=Decimal(equity),
        position_value=Decimal(0),
        equity=Decimal(equity),
    )


def _bar(d: str) -> Bar:
    return Bar(
        ts=datetime.fromisoformat(d),
        open=Decimal("1.00"),
        high=Decimal("1.00"),
        low=Decimal("1.00"),
        close=Decimal("1.00"),
        volume=Decimal("0"),
    )


def test_total_return(make_config: MakeConfig) -> None:
    eq = (_eq("100"), _eq("110"), _eq("105"))
    bars = (_bar("2024-01-01"), _bar("2024-01-02"), _bar("2024-01-03"))
    m = compute_metrics(
        eq, (), bars, initial_cash=Decimal("100"), config=make_config(), frame=Frame.DAILY
    )
    assert m.total_return == Decimal("5") / Decimal("100")


def test_max_drawdown(make_config: MakeConfig) -> None:
    # 100 -> 120 -> 90 -> 110：峰值 120、谷值 90，回撤 30/120
    eq = (_eq("100"), _eq("120"), _eq("90"), _eq("110"))
    bars = tuple(_bar(f"2024-01-0{i}") for i in range(1, 5))
    m = compute_metrics(
        eq, (), bars, initial_cash=Decimal("100"), config=make_config(), frame=Frame.DAILY
    )
    assert m.max_drawdown == Decimal("30") / Decimal("120")


def test_win_rate_and_pl_ratio(make_config: MakeConfig) -> None:
    eq = (_eq("100"), _eq("100"))
    bars = (_bar("2024-01-01"), _bar("2024-07-02"))
    fills = (
        Fill(Side.SELL, Decimal("1.10"), 100, Decimal("0.1"), 0, realized_pnl=Decimal("100")),
        Fill(Side.SELL, Decimal("1.10"), 100, Decimal("0.1"), 0, realized_pnl=Decimal("-50")),
        Fill(Side.SELL, Decimal("1.10"), 100, Decimal("0.1"), 0, realized_pnl=Decimal("200")),
    )
    m = compute_metrics(
        eq, fills, bars, initial_cash=Decimal("100"), config=make_config(), frame=Frame.DAILY
    )
    assert m.win_rate == Decimal(2) / Decimal(3)
    assert m.profit_loss_ratio == Decimal("3")  # 平均盈 150 / 平均亏 50


def test_sharpe_positive_for_monotonic_gain(make_config: MakeConfig) -> None:
    eq = tuple(_eq(str(100 + i)) for i in range(10))  # 单调递增
    bars = tuple(_bar(f"2024-01-{i:02d}") for i in range(1, 11))
    m = compute_metrics(
        eq, (), bars, initial_cash=Decimal("100"), config=make_config(), frame=Frame.DAILY
    )
    assert m.sharpe > 0


def test_buy_hold_positive_when_price_up(make_config: MakeConfig) -> None:
    bars = (
        Bar(
            ts=datetime(2024, 1, 1),
            open=Decimal("1.00"),
            high=Decimal("1.00"),
            low=Decimal("1.00"),
            close=Decimal("1.00"),
            volume=Decimal("0"),
        ),
        Bar(
            ts=datetime(2024, 1, 2),
            open=Decimal("1.10"),
            high=Decimal("1.10"),
            low=Decimal("1.10"),
            close=Decimal("1.10"),
            volume=Decimal("0"),
        ),
    )
    m = compute_metrics(
        (_eq("2000"), _eq("2000")),
        (),
        bars,
        initial_cash=Decimal("2000"),
        config=make_config(),
        frame=Frame.DAILY,
    )
    assert m.buy_hold_return > 0


def test_buy_hold_uses_initial_cash_denominator(make_config: MakeConfig) -> None:
    """回归 #10：买入持有分母用 initial_cash（与网格 total_return 同口径），非实际投入。"""
    bars = (
        Bar(
            ts=datetime(2024, 1, 1),
            open=Decimal("1.40"),
            high=Decimal("1.40"),
            low=Decimal("1.40"),
            close=Decimal("1.40"),
            volume=Decimal("0"),
        ),
        Bar(
            ts=datetime(2024, 1, 2),
            open=Decimal("1.54"),
            high=Decimal("1.54"),
            low=Decimal("1.54"),
            close=Decimal("1.54"),
            volume=Decimal("0"),
        ),
    )
    # 本金 150 只买得起 100 份 @1.40（成本 140.10），10 元零头闲置；
    # @1.54 卖得 153.90，净 13.80 → 分母是本金 150，不是投入的 140.10
    m = compute_metrics(
        (_eq("150"), _eq("150")),
        (),
        bars,
        initial_cash=Decimal("150"),
        config=make_config(),
        frame=Frame.DAILY,
    )
    assert m.buy_hold_return == Decimal("13.80") / Decimal("150")


def test_fee_and_count_aggregation(make_config: MakeConfig) -> None:
    eq = (_eq("100"), _eq("100"))
    bars = (_bar("2024-01-01"), _bar("2024-07-02"))
    fills = (
        Fill(Side.BUY, Decimal("1.00"), 100, Decimal("0.1"), 0),
        Fill(Side.SELL, Decimal("1.10"), 100, Decimal("0.2"), 0, realized_pnl=Decimal("10")),
    )
    m = compute_metrics(
        eq, fills, bars, initial_cash=Decimal("100"), config=make_config(), frame=Frame.DAILY
    )
    assert m.total_fee == Decimal("0.3")
    assert m.n_buys == 1
    assert m.n_sells == 1
