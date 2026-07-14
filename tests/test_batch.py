"""批量回测单测：纯函数 backtest_one + run_batch 编排 / 排序 / 跳过。合成行情，不碰网络。"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal

from vgrid.batch import run_batch
from vgrid.batch.runner import backtest_one
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.enums import Frame
from vgrid.dca.config import DcaConfig, Frequency


def _bars(symbol: str, n: int = 120, drift: float = 0.001) -> BarSeries:
    start = date(2022, 1, 3)
    out = []
    for i in range(n):
        d = start + timedelta(days=i)
        p = Decimal(str(1.0 + 0.05 * math.sin(i / 6) + drift * i))
        out.append(Bar(ts=datetime(d.year, d.month, d.day), open=p, high=p + Decimal("0.01"),
                       low=p - Decimal("0.01"), close=p, volume=Decimal("10000")))
    return BarSeries(symbol=symbol, frame=Frame.DAILY, bars=tuple(out))


def _config() -> DcaConfig:
    return DcaConfig(symbol="PLACEHOLDER", frequency=Frequency.MONTHLY,
                     base_amount=Decimal("2000"), cash_cap=Decimal("50000"), day_of_month=1)


def test_backtest_one_fills_metrics() -> None:
    row = backtest_one(_bars("510880"), _config(), name="红利ETF")
    assert row.ok and row.code == "510880" and row.name == "红利ETF"
    assert row.n_buys is not None and row.n_buys > 0
    assert row.buy_hold_return is not None  # 一次性买入对照一并算出


def test_backtest_one_empty_series_marks_failed() -> None:
    empty = BarSeries(symbol="000000", frame=Frame.DAILY, bars=())
    row = backtest_one(empty, _config(), name="空")
    assert not row.ok and row.reason == "无行情数据" and row.n_buys is None


def test_run_batch_sorts_and_skips() -> None:
    # 注入假 loader：涨得多的 drift 大；一个 symbol 返回空（触发跳过）。
    series = {
        "AAA": _bars("AAA", drift=0.003),   # 涨最多
        "BBB": _bars("BBB", drift=0.001),
        "EMPTY": BarSeries(symbol="EMPTY", frame=Frame.DAILY, bars=()),
    }

    def _loader(code: str, start: date, end: date, frame: Frame) -> BarSeries:
        return series[code]

    result = run_batch(
        ["BBB", "AAA", "EMPTY"], _config(),
        start=date(2022, 1, 1), end=date(2022, 12, 31),
        names={"AAA": "涨多", "BBB": "涨少"}, sort_key="buy_hold_return", loader=_loader,
    )
    assert len(result.ok_rows) == 2
    assert len(result.failed_rows) == 1 and result.failed_rows[0].code == "EMPTY"
    # 按一次性买入收益率降序：涨最多的 AAA 排第一。
    assert result.ok_rows[0].code == "AAA"
    assert result.ok_rows[0].buy_hold_return >= result.ok_rows[1].buy_hold_return


def test_run_batch_drawdown_sort_ascending() -> None:
    series = {"AAA": _bars("AAA", drift=0.003), "BBB": _bars("BBB", drift=0.001)}

    def _loader(code: str, start: date, end: date, frame: Frame) -> BarSeries:
        return series[code]

    result = run_batch(
        ["AAA", "BBB"], _config(), start=date(2022, 1, 1), end=date(2022, 12, 31),
        sort_key="max_drawdown", loader=_loader,
    )
    # 回撤升序：小的排前。
    assert result.ok_rows[0].dca_max_drawdown <= result.ok_rows[1].dca_max_drawdown
