"""红利 ETF 收益对比渲染（终端 + Markdown + CSV）。纯展示层，无单测。

排名表把四口径收益、再投年化 / 回撤、分红率、费用、数据质量并排看。费用只展示不扣费
（真实价格 / 净值本就含费，避免重复扣）；再投的 XIRR 口径与年化不同，报告里点明别直接比。
"""

from __future__ import annotations

import csv
import io
from datetime import date

from vgrid.income.combo import ComboResult
from vgrid.income.metrics import DataQuality, IncomeMetrics
from vgrid.income.report import EtfIncomeResult
from vgrid.income.service import IncomeCompareRun
from vgrid.report._format import cash, pct

_QUALITY_LABEL = {
    DataQuality.OK: "完整",
    DataQuality.PARTIAL: "有缺口",
    DataQuality.MISSING_DIVIDEND: "缺分红",
    DataQuality.MISSING_NAV: "缺净值",
    DataQuality.PRICE_ONLY: "仅价格",
}


def _opt_pct(value: object) -> str:
    return "—" if value is None else pct(value)  # type: ignore[arg-type]


def _quality(m: IncomeMetrics) -> str:
    return _QUALITY_LABEL[m.data_quality]


def _expense(m: IncomeMetrics) -> str:
    return "unknown" if m.total_expense_rate is None else pct(m.total_expense_rate)


def render_income_summary(run: IncomeCompareRun) -> str:
    """终端摘要：池规模 + 排名表头几列。"""
    spec = run.spec
    rows = run.comparison.results
    head = (
        f"红利 ETF 对比（{spec.start} ~ {spec.end}，起始现金 {cash(spec.initial_cash)} 元）\n"
        f"  池 {run.pool_size} 只，纳入 {len(rows)} 只"
        + (f"，跳过 {len(run.skipped)} 只（无日线）" if run.skipped else "")
        + f"，排序 {'→'.join(run.comparison.sort_keys)}\n"
        f"  {'#':<3}{'代码':<8}{'名称':<16}{'再投年化':>10}{'再投收益':>10}"
        f"{'最大回撤':>10}{'近12月分红率':>12}{'费用':>8}{'质量':>7}"
    )
    lines = [head]
    for i, r in enumerate(rows, 1):
        m = r.metrics
        lines.append(
            f"  {i:<3}{r.code:<8}{r.name[:15]:<16}{pct(m.annualized_return):>10}"
            f"{pct(m.reinvest_return):>10}{pct(m.max_drawdown):>10}"
            f"{pct(m.ttm_dividend_yield):>12}{_expense(m):>8}{_quality(m):>7}",
        )
    return "\n".join(lines)


def _ranking_table(rows: list[EtfIncomeResult]) -> list[str]:
    lines = [
        "| # | 代码 | 名称 | 价格 | 现金分红 | 分红再投 | 累计净值 | 再投年化 | 最大回撤 |"
        " 样本分红率 | 近12月分红率 | 费用 | 数据质量 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        m = r.metrics
        lines.append(
            f"| {i} | {r.code} | {r.name} | {pct(m.price_return)} | "
            f"{pct(m.cash_dividend_return)} | {pct(m.reinvest_return)} | "
            f"{_opt_pct(m.acc_nav_return)} | {pct(m.annualized_return)} | "
            f"{pct(m.max_drawdown)} | {pct(m.sample_dividend_yield)} | "
            f"{pct(m.ttm_dividend_yield)} | {_expense(m)} | {_quality(m)} |",
        )
    return lines


def _dividend_detail(rows: list[EtfIncomeResult]) -> list[str]:
    lines = ["## 分红明细摘要", ""]
    for r in rows:
        m = r.metrics
        lifetime = "—" if m.lifetime_per_share is None else str(m.lifetime_per_share)
        recent = "、".join(
            f"{e.ex_date} {e.per_share}" for e in r.dividends[-5:]
        ) or "样本期内无分红"
        lines.extend(
            [
                f"- **{r.code} {r.name}**：样本期分红 {m.n_dividends} 次、"
                f"每份合计 {m.sample_per_share}（历史累计每份 {lifetime}）；"
                f"最近：{recent}",
            ],
        )
    lines.append("")
    return lines


def _quality_notes(rows: list[EtfIncomeResult]) -> list[str]:
    flagged = [(r, w) for r in rows for w in r.metrics.warnings]
    if not flagged:
        return []
    lines = ["## 数据质量提示", ""]
    lines.extend(f"- {r.code} {r.name}：{w}" for r, w in flagged)
    lines.append("")
    return lines


def render_income_report(run: IncomeCompareRun) -> str:
    """完整 Markdown 报告。"""
    spec = run.spec
    rows = run.comparison.results
    skipped_note = (
        f"，跳过 {len(run.skipped)} 只（无日线：{'、'.join(run.skipped)}）" if run.skipped else ""
    )
    lines: list[str] = [
        "# 红利 ETF 分红收益对比报告",
        "",
        f"- 区间：{spec.start} ~ {spec.end}",
        f"- 起始现金：{cash(spec.initial_cash)} 元（各口径同基准满仓建仓）",
        f"- 池：{run.pool_size} 只，纳入 {len(rows)} 只{skipped_note}",
        f"- 排序：{' → '.join(run.comparison.sort_keys)}",
        "",
        "## 横向排名",
        "",
        *_ranking_table(rows),
        "",
        *_dividend_detail(rows),
        "## 费用与口径说明",
        "",
        "> 管理费 / 托管费 / 销售服务费基金每日从资产中计提，公布的净值与场内价**已内含**，"
        "故真实价格 / 净值口径下**不额外扣费**（避免重复扣）。费用列仅作展示，`unknown` 表示"
        "暂无可用费率源。",
        "> 「分红再投年化」是自然日复利（CAGR）；累计净值是含历史分红的长期校验基准，两者差异"
        "过大时会在下方数据质量里提示口径可能不一致。",
        "",
        *_quality_notes(rows),
    ]
    return "\n".join(lines)


def render_combo_summary(
    result: ComboResult, *, symbol: str, strategy: str, start: date, end: date
) -> str:
    """红利增强回测终端摘要：策略 vs 分红再投增强 + 分红贡献。"""
    return "\n".join(
        [
            f"红利增强回测（{symbol} · {strategy} · {start} ~ {end}）",
            f"  策略收益（价格口径，不含分红）：{pct(result.strategy_return)}",
            f"  分红再投增强后收益：           {pct(result.enhanced_return)}",
            f"  分红贡献（增强 − 策略）：       {pct(result.dividend_boost)}",
            f"  期间累计到账分红：{cash(result.dividend_cash_total)} 元，"
            f"再投买入 {result.reinvest_shares} 份",
            "  注：策略跑在不复权价上（除权日真跌），分红按持仓在发放日到账、下一开盘再投。",
        ],
    )


def render_income_csv(run: IncomeCompareRun) -> str:
    """一行一个 ETF 的指标 CSV。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "排名", "代码", "名称", "数据质量", "价格收益率", "现金分红收益率",
            "分红再投收益率", "累计净值收益率", "再投年化", "最大回撤", "分红次数",
            "样本期每份分红", "样本期分红率", "近12月分红率", "费用合计年费率",
            "样本起", "样本止",
        ],
    )
    for i, r in enumerate(run.comparison.results, 1):
        m = r.metrics
        writer.writerow(
            [
                i, r.code, r.name, m.data_quality.value,
                pct(m.price_return), pct(m.cash_dividend_return), pct(m.reinvest_return),
                _opt_pct(m.acc_nav_return), pct(m.annualized_return), pct(m.max_drawdown),
                m.n_dividends, str(m.sample_per_share), pct(m.sample_dividend_yield),
                pct(m.ttm_dividend_yield), _expense(m), m.sample_start, m.sample_end,
            ],
        )
    return buf.getvalue()
