"""分享图冒烟测：每张图用合成数据跑通渲染、产出非空 PNG（不测审美，展示层规范）。"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境也跑得动

import pytest
from matplotlib.figure import Figure

from vgrid.backtest.compare import compare_strategies
from vgrid.backtest.matcher import simulate_with_engine
from vgrid.charts import (
    render_backtest_chart,
    render_compare_chart,
    render_enhance_chart,
    render_income_chart,
    render_ladder_chart,
    render_scan_heatmap,
    save_png,
)
from vgrid.cli.app import _save_chart
from vgrid.core.bar import Bar, BarSeries
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.core.fees import FeeModel
from vgrid.dca.config import DcaConfig, Frequency
from vgrid.income.combo import dca_dividend_combo
from vgrid.income.models import DividendEvent, ExpenseInfo, NavPoint
from vgrid.income.report import build_etf_result
from vgrid.scan.runner import run_scan
from vgrid.scan.space import ScanSpec
from vgrid.strategy.ladder_view import build_ladder_view


def _bars(n: int = 120, start: date = date(2024, 1, 2)) -> tuple[Bar, ...]:
    out = []
    for i in range(n):
        d = start + timedelta(days=i)
        p = Decimal(str(1.0 + 0.05 * math.sin(i / 6) + 0.001 * i))
        out.append(Bar(ts=datetime(d.year, d.month, d.day), open=p, high=p + Decimal("0.01"),
                       low=p - Decimal("0.01"), close=p, volume=Decimal("10000")))
    return tuple(out)


def _series() -> BarSeries:
    return BarSeries(symbol="510880", frame=Frame.DAILY, bars=_bars())


def _grid() -> GridConfig:
    return GridConfig(symbol="510880", lower_price=Decimal("0.95"), upper_price=Decimal("1.15"),
                      grid_count=10, per_grid_amount=Decimal("2000"), capital_cap=Decimal("50000"))


def _assert_png(fig, tmp_path: Path, name: str) -> None:
    p = save_png(fig, tmp_path / name)
    assert p.exists() and p.stat().st_size > 5_000


def test_backtest_chart(tmp_path: Path) -> None:
    res, _ = simulate_with_engine(_grid(), _series())
    _assert_png(render_backtest_chart(res, symbol="510880"), tmp_path, "bt.png")


def test_ladder_chart(tmp_path: Path) -> None:
    _, engine = simulate_with_engine(_grid(), _series())
    price = _series().bars[-1].close
    view = build_ladder_view(engine, price)
    _assert_png(render_ladder_chart(view, symbol="510880"), tmp_path, "ladder.png")


def test_compare_chart(tmp_path: Path) -> None:
    dca = DcaConfig(symbol="510880", frequency=Frequency.MONTHLY,
                    base_amount=Decimal("2000"), cash_cap=Decimal("50000"))
    cmp = compare_strategies(_series(), initial_cash=Decimal("50000"),
                             grid_config=_grid(), dca_config=dca)
    _assert_png(render_compare_chart(cmp), tmp_path, "cmp.png")


def test_income_chart(tmp_path: Path) -> None:
    bars = list(_bars(60))
    navs = [NavPoint(b.ts.date(), Decimal("1.5"), Decimal("2.0")) for b in bars]
    divs = [DividendEvent(b.ts.date(), b.ts.date(), b.ts.date(), Decimal("0.02"))
            for b in bars[20::20]]
    res = build_etf_result(code="510880", name="红利ETF", bars=bars, dividends=divs,
                           navs=navs, expenses=ExpenseInfo.unknown(),
                           initial_cash=Decimal("10000"), lot_size=100, fee=FeeModel())
    _assert_png(render_income_chart(res), tmp_path, "income.png")


def test_enhance_chart(tmp_path: Path) -> None:
    bars = _series()
    divs = [DividendEvent(b.ts.date(), b.ts.date(), b.ts.date(), Decimal("0.05"))
            for b in bars.bars[30::30]]
    cfg = DcaConfig(symbol="510880", frequency=Frequency.MONTHLY,
                    base_amount=Decimal("2000"), cash_cap=Decimal("50000"))
    res = dca_dividend_combo(cfg, bars, divs)
    _assert_png(render_enhance_chart(res, symbol="510880", strategy="定投"),
                tmp_path, "enhance.png")


def test_scan_heatmap(tmp_path: Path) -> None:
    spec = ScanSpec(
        fixed={"symbol": "510880", "lower_price": Decimal("0.95"), "upper_price": Decimal("1.15"),
               "capital_cap": Decimal("50000")},
        vary={"grid_count": [6, 10, 14],
              "per_grid_amount": [Decimal("1000"), Decimal("2000"), Decimal("3000")]},
    )
    rows = run_scan(spec.expand(), _series(), initial_cash=Decimal("50000"))
    fig = render_scan_heatmap(list(rows), metric="sharpe", spec=spec)
    _assert_png(fig, tmp_path, "scan.png")


def test_cli_save_chart_writes_png(tmp_path: Path) -> None:
    """CLI --chart 的落盘胶水：跑渲染 thunk → PNG 落在 out_dir，文件名带 .png。"""
    def _render() -> Figure:
        res, _ = simulate_with_engine(_grid(), _series())
        return render_backtest_chart(res, symbol="510880")

    _save_chart(_render, tmp_path, "510880_backtest")
    out = tmp_path / "510880_backtest.png"
    assert out.exists() and out.stat().st_size > 5_000


def test_scan_heatmap_rejects_non_2d() -> None:
    spec = ScanSpec(fixed={"symbol": "510880", "lower_price": Decimal("0.95"),
                           "upper_price": Decimal("1.15"), "capital_cap": Decimal("50000")},
                    vary={"grid_count": [6, 10]})
    with pytest.raises(ValueError, match="2 个扫描维度"):
        render_scan_heatmap([], metric="sharpe", spec=spec)
