"""批量回测编排：同一份定投配置，跑一串 ETF，逐只出定投 + 一次性买入对照。

``backtest_one`` 是纯函数（吃 BarSeries，不碰 I/O，单测重点）；``run_batch`` 逐只拉行情、
调 ``backtest_one``、收集成 ``BatchResult`` 并排序。某只无数据不崩，标记跳过继续跑。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from vgrid.batch.models import BatchResult, BatchRow
from vgrid.core.enums import Frame
from vgrid.data.loader import load_bars
from vgrid.dca.config import DcaConfig
from vgrid.dca.engine import run_dca

if TYPE_CHECKING:
    from vgrid.core.bar import BarSeries

#: 拉行情的函数签名（默认走 load_bars，测试可注入假实现）。
BarsLoader = Callable[[str, date, date, Frame], "BarSeries"]


def _default_loader(refresh: bool) -> BarsLoader:
    def _load(code: str, start: date, end: date, frame: Frame) -> BarSeries:
        # 前复权：分红按再投折进价格，算总收益口径一致。
        return load_bars(code, start, end, frame, adjust="qfq", refresh=refresh)

    return _load


def backtest_one(series: BarSeries, config: DcaConfig, *, name: str) -> BatchRow:
    """对单只已加载的行情跑定投回测，返回一行结果（纯函数，无 I/O）。"""
    code = series.symbol
    if not series.bars:
        return BatchRow.failed(code, name, "无行情数据")
    # 配置是模板，换成这只的代码再跑。
    result = run_dca(dataclasses.replace(config, symbol=code), series)
    m = result.metrics
    return BatchRow(
        code=code,
        name=name,
        ok=True,
        dca_return=m.profit_rate_on_invested,
        dca_xirr=m.xirr,
        dca_max_drawdown=m.max_drawdown,
        invested=m.invested_amount,
        n_buys=m.n_buys,
        skipped=m.skipped_count,
        total_fee=m.total_fee,
        buy_hold_return=m.buy_hold_return,
    )


#: 无回撤值时的排序哨兵：当成极大，回撤升序里排最后。
_DRAWDOWN_SENTINEL = Decimal("9" * 18)
#: 排序键 → BatchRow 属性名（回撤单独处理）。
_SORT_ATTR = {"xirr": "dca_xirr", "dca_return": "dca_return", "buy_hold_return": "buy_hold_return"}


def _sort_rows(rows: list[BatchRow], sort_key: str) -> list[BatchRow]:
    """按指标排序：回撤越小越好（升序），其余越大越好（降序）。无值的排最后。"""
    ok = [r for r in rows if r.ok]
    bad = [r for r in rows if not r.ok]
    if sort_key == "max_drawdown":
        ok.sort(key=lambda r: r.dca_max_drawdown if r.dca_max_drawdown is not None
                else _DRAWDOWN_SENTINEL)
    else:
        attr = _SORT_ATTR.get(sort_key, "dca_xirr")
        ok.sort(key=lambda r: (getattr(r, attr) is not None, getattr(r, attr) or Decimal(0)),
                reverse=True)
    return ok + bad


def run_batch(
    codes: list[str],
    config: DcaConfig,
    *,
    start: date,
    end: date,
    frame: Frame = Frame.DAILY,
    names: Mapping[str, str] | None = None,
    sort_key: str = "xirr",
    loader: BarsLoader | None = None,
    refresh: bool = False,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> BatchResult:
    """逐只跑批量回测，收集并排序。某只拉数/回测失败标记跳过，不中断整批。"""
    load = loader or _default_loader(refresh)
    name_map = names or {}
    rows: list[BatchRow] = []
    total = len(codes)
    for i, code in enumerate(codes, 1):
        name = name_map.get(code, code)
        if on_progress is not None:
            on_progress(i, total, code)
        try:
            series = load(code, start, end, frame)
            rows.append(backtest_one(series, config, name=name))
        except (ValueError, KeyError, OSError) as e:
            rows.append(BatchRow.failed(code, name, str(e)))
    ordered = _sort_rows(rows, sort_key)
    return BatchResult(
        rows=tuple(ordered),
        start=start.isoformat(),
        end=end.isoformat(),
        frame=frame.value,
        sort_key=sort_key,
    )
