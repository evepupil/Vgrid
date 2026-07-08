"""三方对比渲染（终端表 + Markdown）。纯展示层，无单测。

同一笔起始现金下，网格 / 定投 / 买入持有的末权益、收益率、回撤、手续费并排看。定投多给
「实际投入 + XIRR」两列（它分批进场，只看对起始现金的收益率会低估资金效率）。
"""

from __future__ import annotations

from decimal import Decimal

from vgrid.backtest.compare import StrategyComparison
from vgrid.report._format import cash, pct


def _xirr(value: Decimal | None) -> str:
    return "—" if value is None else pct(value)


def _invested(value: Decimal | None) -> str:
    return "—" if value is None else cash(value)


def render_comparison(comparison: StrategyComparison) -> str:
    """终端对比表。"""
    first_day = comparison.bars[0].ts.date()
    last_day = comparison.bars[-1].ts.date()
    header = (
        f"策略对比（{first_day} ~ {last_day}，{len(comparison.bars)} 根，"
        f"起始现金 {cash(comparison.initial_cash)} 元）\n"
        f"  {'策略':<8}{'末权益':>14}{'净利':>13}{'收益率':>10}"
        f"{'年化':>10}{'最大回撤':>10}{'手续费':>10}{'笔数':>6}"
    )
    lines = [header]
    for r in comparison.rows:
        lines.append(
            f"  {r.name:<8}{cash(r.final_equity):>14}{cash(r.profit):>13}"
            f"{pct(r.total_return):>10}{pct(r.annualized_return):>10}"
            f"{pct(r.max_drawdown):>10}{cash(r.total_fee):>10}{r.n_trades:>6}"
        )
        if r.invested is not None or r.xirr is not None:
            lines.append(f"  {'':<8}└ 实际投入 {_invested(r.invested)} · XIRR {_xirr(r.xirr)}")
    return "\n".join(lines)


def render_comparison_report(comparison: StrategyComparison) -> str:
    """Markdown 对比报告。"""
    first_day = comparison.bars[0].ts.date()
    last_day = comparison.bars[-1].ts.date()
    lines: list[str] = [
        "# 策略对比报告",
        "",
        f"- 区间：{first_day} ~ {last_day}（{len(comparison.bars)} 根）",
        f"- 起始现金：{cash(comparison.initial_cash)} 元（三方同口径）",
        "",
        "| 策略 | 末权益 | 净利 | 收益率 | 年化 | 最大回撤 | 手续费 | 笔数 | 实际投入 | XIRR |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in comparison.rows:
        lines.append(
            f"| {r.name} | {cash(r.final_equity)} | {cash(r.profit)} | "
            f"{pct(r.total_return)} | {pct(r.annualized_return)} | {pct(r.max_drawdown)} | "
            f"{cash(r.total_fee)} | {r.n_trades} | {_invested(r.invested)} | {_xirr(r.xirr)} |"
        )
    lines.extend(
        [
            "",
            "> 注：收益率一律对**起始现金**算（同一笔钱、同一段行情谁最后更有钱）。定投的钱分批"
            "进场，只看这个收益率会低估它的资金效率，故另给「实际投入」和 **XIRR**（按每笔投入"
            "时间贴现的真实年化）。年化为自然日复利（CAGR），和 XIRR 口径不同，别直接相较。",
            "",
        ]
    )
    return "\n".join(lines)
