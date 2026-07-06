"""把 BacktestResult 渲染成 Markdown 报告。

纯展示层（无单测）：策略参数表、关键指标 + 买入持有对比、手续费明细、成交明细。
落盘由调用方（CLI）负责，本函数只产出文本。
"""

from __future__ import annotations

from vgrid.backtest.result import BacktestResult
from vgrid.core.config import GridConfig
from vgrid.report._format import cash, dec, pct

_FILL_PREVIEW = 20  # 报告里列出的成交明细笔数上限


def render_report(result: BacktestResult, config: GridConfig) -> str:
    """渲染完整 Markdown 报告。"""
    m = result.metrics
    first_day = result.bars[0].ts.date()
    last_day = result.bars[-1].ts.date()

    lines: list[str] = [
        f"# 网格回测报告 · {config.symbol}",
        "",
        "## 策略参数",
        "",
        "| 参数 | 值 |",
        "|---|---|",
        f"| 标的 | {config.symbol} |",
        f"| 网格区间 | {config.lower_price} ~ {config.upper_price} |",
        f"| 格数 | {config.grid_count} |",
        f"| 每格金额 | {config.per_grid_amount} 元 |",
        f"| 资金上限 | {config.capital_cap} 元 |",
        f"| 间距模式 | {config.spacing_mode.value} |",
        f"| 建仓模式 | {config.base_build_mode.value} |",
        f"| 上破重建比例 | {config.upper_rebuild_ratio} |",
        f"| 下沿放大·间距 | ×{config.down_spacing_factor} |",
        f"| 下沿放大·金额 | ×{config.down_amount_factor} |",
        f"| 回测区间 | {first_day} ~ {last_day}（{len(result.bars)} 根） |",
        "",
        "## 关键指标",
        "",
        "| 指标 | 网格策略 | 买入持有 |",
        "|---|---|---|",
        f"| 总收益率 | {pct(m.total_return)} | {pct(m.buy_hold_return)} |",
        f"| 年化收益率 | {pct(m.annualized_return)} | — |",
        f"| 最大回撤 | {pct(m.max_drawdown)} | — |",
        f"| 夏普 | {dec(m.sharpe)} | — |",
        f"| 胜率 | {pct(m.win_rate)} | — |",
        f"| 盈亏比 | {dec(m.profit_loss_ratio)} | — |",
        f"| 末权益 | {cash(m.final_equity)} 元 | — |",
        "",
        "## 手续费",
        "",
        f"- 累计手续费：**{cash(m.total_fee)}** 元",
        f"- 成交笔数：买入 {m.n_buys} 笔 / 卖出 {m.n_sells} 笔",
        "",
        f"## 成交明细（前 {_FILL_PREVIEW} 笔）",
        "",
        "| 时间 | 方向 | 价格 | 份额 | 手续费 | 已实现盈亏 |",
        "|---|---|---|---|---|---|",
    ]

    for f in result.fills[:_FILL_PREVIEW]:
        pnl = "—" if f.realized_pnl is None else cash(f.realized_pnl)
        lines.append(
            f"| {f.ts} | {f.side.value} | {f.price} | {f.shares} | {cash(f.fee)} | {pnl} |"
        )
    if len(result.fills) > _FILL_PREVIEW:
        lines.append(f"| … | 共 {len(result.fills)} 笔 | | | | |")
    lines.append("")
    return "\n".join(lines)
