"""批量回测渲染（终端摘要 + Markdown 排名表）。纯展示层，无单测。

把 N 只 ETF 的定投表现 + 同期一次性买入并排排名。定投的 XIRR 是资金加权真实年化，
一次性买入的收益率是对起始现金的总收益——两者口径不同，表里各列一栏，别直接比大小。
"""

from __future__ import annotations

from vgrid.batch.models import BatchResult, BatchRow
from vgrid.report._format import cash, pct

_SORT_LABEL = {
    "xirr": "定投 XIRR",
    "dca_return": "定投收益率",
    "buy_hold_return": "一次性买入收益率",
    "max_drawdown": "定投最大回撤",
}


def _opt_pct(value: object) -> str:
    return "—" if value is None else pct(value)  # type: ignore[arg-type]


def _opt_cash(value: object) -> str:
    return "—" if value is None else cash(value)  # type: ignore[arg-type]


def render_batch_summary(result: BatchResult) -> str:
    """终端摘要：区间 + 排序键 + 跑成/跳过数 + 前几名。"""
    ok = result.ok_rows
    bad = result.failed_rows
    label = _SORT_LABEL.get(result.sort_key, result.sort_key)
    lines = [
        f"批量回测（{result.start} ~ {result.end}，{len(ok)} 只跑成 / {len(bad)} 只跳过，"
        f"按 `{label}` 排序）",
        f"  {'代码':<8}{'名称':<12}{'定投XIRR':>10}{'定投收益':>10}"
        f"{'定投回撤':>10}{'一次性':>10}{'笔数':>6}",
    ]
    for r in ok:
        lines.append(
            f"  {r.code:<8}{_clip(r.name, 10):<12}{_opt_pct(r.dca_xirr):>10}"
            f"{_opt_pct(r.dca_return):>10}{_opt_pct(r.dca_max_drawdown):>10}"
            f"{_opt_pct(r.buy_hold_return):>10}{_int(r.n_buys):>6}"
        )
    for r in bad:
        lines.append(f"  {r.code:<8}{_clip(r.name, 10):<12}  跳过：{r.reason}")
    return "\n".join(lines)


def render_batch_report(result: BatchResult) -> str:
    """Markdown 排名表 + 口径说明。"""
    label = _SORT_LABEL.get(result.sort_key, result.sort_key)
    head = (
        f"# 批量回测排名\n\n"
        f"- 区间：{result.start} ~ {result.end}（{result.frame}）\n"
        f"- 排序：{label}\n"
        f"- 跑成 {len(result.ok_rows)} 只 / 跳过 {len(result.failed_rows)} 只\n\n"
    )
    header = ("| 代码 | 名称 | 定投XIRR | 定投收益率 | 定投回撤 | 一次性买入收益率 "
              "| 投入本金 | 笔数 | 跳过 | 手续费 |")
    table = [header, "|---|---|---|---|---|---|---|---|---|---|"]
    for r in result.ok_rows:
        table.append(_md_row(r))
    for r in result.failed_rows:
        table.append(
            f"| {r.code} | {_clip(r.name, 12)} | — | — | — | — | — | — | — | 跳过：{r.reason} |"
        )
    note = (
        "\n\n> 口径：定投 XIRR = 资金加权真实年化（每笔钱按进场时间算）；一次性买入收益率 = "
        "对起始现金的总收益。两者口径不同，别直接比大小。前复权价、分红默认再投。\n"
        "> 上市晚的标的实际区间短（看「笔数」列，差得多说明区间不一致），XIRR 排名别跨区间硬比。\n"
        "> 样本内历史回测，过去不代表未来。"
    )
    return head + "\n".join(table) + note


def _md_row(r: BatchRow) -> str:
    return (
        f"| {r.code} | {_clip(r.name, 12)} | {_opt_pct(r.dca_xirr)} "
        f"| {_opt_pct(r.dca_return)} | {_opt_pct(r.dca_max_drawdown)} "
        f"| {_opt_pct(r.buy_hold_return)} | {_opt_cash(r.invested)} "
        f"| {_int(r.n_buys)} | {_int(r.skipped)} | {_opt_cash(r.total_fee)} |"
    )


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _int(value: int | None) -> str:
    return "—" if value is None else str(value)
