"""定投回测引擎测试：成交 / 现金上限 / 取整跳过 / 加码 / 指标。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.dca.config import AmountMode, AmountPolicy, DcaConfig, DrawdownTier, Frequency
from vgrid.dca.engine import run_dca


def _series(rows: list[tuple[date, str]]) -> BarSeries:
    """rows: (日期, 价格) —— open=high=low=close=价格，方便算账。"""
    bars = []
    for d, price in rows:
        p = Decimal(price)
        ts = datetime(d.year, d.month, d.day)
        bars.append(Bar(ts=ts, open=p, high=p, low=p, close=p, volume=Decimal("1000")))
    return BarSeries(symbol="159920", frame=Frame.DAILY, bars=tuple(bars))


def _cfg(**kw: object) -> DcaConfig:
    base: dict[str, object] = {
        "symbol": "159920",
        "frequency": Frequency.DAILY,
        "base_amount": Decimal("2000"),
        "cash_cap": Decimal("50000"),
    }
    base.update(kw)
    return DcaConfig(**base)  # type: ignore[arg-type]


def test_fixed_daily_precise() -> None:
    bars = _series([(date(2024, 1, d), "1.00") for d in (2, 3, 4)])
    res = run_dca(_cfg(), bars)
    m = res.metrics
    assert m.n_buys == 3
    assert all(t.shares == 2000 for t in res.trades)
    assert m.invested_amount == Decimal("6000")
    assert m.total_fee == Decimal("0.3")  # 每笔 max(0.1, 2000×0.00005=0.1) = 0.1
    assert m.final_cash == Decimal("43999.7")  # 50000 − 3×2000.1
    assert m.final_market_value == Decimal("6000")
    assert m.profit == Decimal("-0.3")  # 价平，只亏手续费
    assert m.profit_on_invested == Decimal("0")


def test_cash_cap_stops_buying() -> None:
    bars = _series([(date(2024, 1, d), "1.00") for d in (2, 3, 4, 5, 8)])
    res = run_dca(_cfg(cash_cap=Decimal("5000"), initial_cash=Decimal("50000")), bars)
    assert res.metrics.invested_amount == Decimal("5000")  # 2000 + 2000 + 1000
    assert res.metrics.n_buys == 3
    assert res.metrics.skipped_count == 2
    assert res.skipped[0].reason == "已达累计投入上限"


def test_skips_when_cannot_fill_a_lot() -> None:
    bars = _series([(date(2024, 1, 2), "1.00"), (date(2024, 1, 3), "1.00")])
    res = run_dca(_cfg(base_amount=Decimal("50")), bars)  # 50 元买不满一手（100 份）
    assert res.metrics.n_buys == 0
    assert res.metrics.skipped_count == 2
    assert res.skipped[0].reason == "买不满一手"


def test_drawdown_amplifies_on_drop() -> None:
    rows = [(date(2024, 1, d), "10.00") for d in (2, 3, 4, 5, 6)]
    rows.append((date(2024, 1, 8), "8.00"))  # 跳空跌到 8，回撤 20%
    bars = _series(rows)
    policy = AmountPolicy(
        mode=AmountMode.DRAWDOWN,
        lookback_days=10,
        tiers=(DrawdownTier(Decimal("0.10"), Decimal("2")),),
    )
    res = run_dca(_cfg(cash_cap=Decimal("100000"), amount_policy=policy), bars)
    assert res.trades[0].multiplier == Decimal("1")  # 首笔无历史高点 → 1 倍
    assert res.trades[5].multiplier == Decimal("2")  # 回撤 20% ≥ 10% 档 → 2 倍
    assert res.trades[5].shares == 500  # 4000 ÷ 8 = 500


def test_rising_price_positive_return() -> None:
    bars = _series(
        [(date(2024, 1, 2), "1.00"), (date(2024, 7, 1), "1.20"), (date(2024, 12, 2), "1.50")]
    )
    res = run_dca(_cfg(), bars)
    m = res.metrics
    assert m.n_buys == 3  # 稀疏 K 线：每根首个覆盖它的日历日买一次
    assert m.profit_on_invested > 0
    assert m.xirr is not None
    assert m.xirr > 0
    assert m.buy_hold_return > 0


def test_empty_bars_raises() -> None:
    with pytest.raises(ValueError, match="至少需要一根"):
        run_dca(_cfg(), BarSeries(symbol="159920", frame=Frame.DAILY, bars=()))
