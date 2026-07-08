"""定投回测报告渲染（终端摘要 + Markdown）。

纯展示层（无单测）：策略参数、关键指标 + 买入持有对照、手续费、成交明细。落盘由调用方
（CLI）负责，本模块只产出文本。和网格报告同风格，方便并读。
"""

from __future__ import annotations

from decimal import Decimal

from vgrid.dca.config import AmountMode, DcaConfig, Frequency
from vgrid.dca.result import DcaResult
from vgrid.report._format import cash, dec, pct

_FILL_PREVIEW = 20  # 报告里列出的成交明细笔数上限


def _xirr(value: Decimal | None) -> str:
    """XIRR 无解时显示「—」。"""
    return "—" if value is None else pct(value)


def _freq_label(config: DcaConfig) -> str:
    if config.frequency is Frequency.WEEKLY:
        return f"每周（周{config.weekday}）"
    if config.frequency is Frequency.MONTHLY:
        return f"每月（{config.day_of_month} 号）"
    return "每日"


def _policy_label(config: DcaConfig) -> str:
    p = config.amount_policy
    if p.mode is AmountMode.DRAWDOWN:
        tiers = "，".join(f"回撤{pct(t.drawdown)}×{t.multiplier}" for t in p.sorted_tiers)
        return f"跌幅加码（回看 {p.lookback_days} 根：{tiers}）"
    if p.mode is AmountMode.MA_DEVIATION:
        return (
            f"均线偏离（MA{p.ma_window}：低于×{p.below_multiplier} / "
            f"持平×{p.normal_multiplier} / 高于×{p.above_multiplier}）"
        )
    return "固定金额"


def render_dca_summary(result: DcaResult, config: DcaConfig) -> str:
    """单屏终端摘要。"""
    m = result.metrics
    first_day = result.bars[0].ts.date()
    last_day = result.bars[-1].ts.date()
    return (
        f"定投回测 · {config.symbol}（{first_day} ~ {last_day}，{len(result.bars)} 根）· "
        f"{_freq_label(config)} · {_policy_label(config)}\n"
        f"  累计投入  {cash(m.invested_amount):>12}    末权益    {cash(m.final_equity):>12}\n"
        f"  账户净利  {cash(m.profit):>12}    投入回报  {pct(m.profit_rate_on_invested):>12}\n"
        f"  XIRR      {_xirr(m.xirr):>12}    买入持有  {pct(m.buy_hold_return):>12}\n"
        f"  最大回撤  {pct(m.max_drawdown):>12}    买入/跳过 {m.n_buys}/{m.skipped_count:>6}\n"
        f"  手续费    {cash(m.total_fee):>12}"
    )


def render_dca_report(result: DcaResult, config: DcaConfig) -> str:
    """渲染完整 Markdown 报告。"""
    m = result.metrics
    first_day = result.bars[0].ts.date()
    last_day = result.bars[-1].ts.date()

    lines: list[str] = [
        f"# 定投回测报告 · {config.symbol}",
        "",
        "## 策略参数",
        "",
        "| 参数 | 值 |",
        "|---|---|",
        f"| 标的 | {config.symbol} |",
        f"| 频率 | {_freq_label(config)} |",
        f"| 每次投入 | {config.base_amount} 元 |",
        f"| 金额规则 | {_policy_label(config)} |",
        f"| 累计投入上限 | {config.cash_cap} 元 |",
        f"| 起始现金 | {config.start_cash} 元 |",
        f"| 回测区间 | {first_day} ~ {last_day}（{len(result.bars)} 根） |",
        "",
        "## 关键指标",
        "",
        "| 指标 | 定投 | 买入持有 |",
        "|---|---|---|",
        f"| 累计投入 | {cash(m.invested_amount)} 元 | — |",
        f"| 末权益 | {cash(m.final_equity)} 元 | — |",
        f"| 账户净利 | {cash(m.profit)} 元 | — |",
        f"| 投入回报率 | {pct(m.profit_rate_on_invested)} | {pct(m.buy_hold_return)} |",
        f"| XIRR（年化） | {_xirr(m.xirr)} | — |",
        f"| 最大回撤 | {pct(m.max_drawdown)} | — |",
        f"| 期末持仓市值 | {cash(m.final_market_value)} 元 | — |",
        f"| 期末现金 | {cash(m.final_cash)} 元 | — |",
        "",
        "> 注：`投入回报率 = (持仓市值 − 累计投入) / 累计投入`，未扣买入手续费（费单列）；"
        "`账户净利 = 末权益 − 起始现金`，已含手续费。XIRR 按每笔投入时间贴现的真实年化。",
        "",
        "## 手续费与执行",
        "",
        f"- 累计手续费：**{cash(m.total_fee)}** 元",
        f"- 买入 {m.n_buys} 笔，跳过 {m.skipped_count} 次（买不满一手 / 触顶 / 现金不足）",
        "",
        f"## 成交明细（前 {_FILL_PREVIEW} 笔）",
        "",
        "| 时间 | 价格 | 份额 | 成交额 | 手续费 | 金额倍数 |",
        "|---|---|---|---|---|---|",
    ]

    for t in result.trades[:_FILL_PREVIEW]:
        lines.append(
            f"| {t.ts} | {t.price} | {t.shares} | {cash(t.notional)} | "
            f"{cash(t.fee)} | ×{dec(t.multiplier)} |"
        )
    if len(result.trades) > _FILL_PREVIEW:
        lines.append(f"| … | 共 {len(result.trades)} 笔 | | | | |")
    lines.append("")
    return "\n".join(lines)
