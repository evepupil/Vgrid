"""终端精简摘要：几行核心指标，跑完回测直接打印。"""

from __future__ import annotations

from vgrid.backtest.result import BacktestResult
from vgrid.core.config import GridConfig
from vgrid.report._format import cash, dec, pct


def render_summary(result: BacktestResult, config: GridConfig) -> str:
    """单屏终端摘要。"""
    m = result.metrics
    first_day = result.bars[0].ts.date()
    last_day = result.bars[-1].ts.date()
    return (
        f"网格回测 · {config.symbol}（{first_day} ~ {last_day}，{len(result.bars)} 根）\n"
        f"  总收益率  {pct(m.total_return):>12}    买入持有  {pct(m.buy_hold_return):>12}\n"
        f"  年化      {pct(m.annualized_return):>12}    最大回撤  {pct(m.max_drawdown):>12}\n"
        f"  夏普      {dec(m.sharpe):>12}    胜率      {pct(m.win_rate):>12}\n"
        f"  末权益    {cash(m.final_equity):>12}    买卖笔数  {m.n_buys}/{m.n_sells:>7}\n"
        f"  手续费    {cash(m.total_fee):>12}"
    )
