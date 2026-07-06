"""vgrid 命令行：回测 / 取数。

两个子命令：
- ``vgrid fetch``    只下载行情并写入本地缓存（预热 / 调试）。
- ``vgrid backtest`` 下载行情 → 跑网格回测 → 终端摘要 + Markdown 报告。

策略参数走 ``--config <cfg.json>``（GridConfig 的 to_dict 格式）；数据区间、标的、
周期走命令行参数。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from vgrid.backtest import simulate
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.report import render_report, render_summary


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "fetch":
        return _cmd_fetch(args)
    return _cmd_backtest(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vgrid", description="ETF 网格回测命令行")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="下载行情并写入本地缓存")
    _add_data_args(p_fetch)

    p_bt = sub.add_parser("backtest", help="下载行情 → 跑回测 → 输出报告")
    _add_data_args(p_bt)
    p_bt.add_argument("--config", type=Path, required=True, help="策略配置 JSON")
    p_bt.add_argument("--out", type=Path, default=Path("reports"), help="报告输出目录")
    p_bt.add_argument(
        "--initial-cash",
        type=Decimal,
        default=None,
        help="初始资金（默认用配置的 capital_cap）",
    )
    return parser


def _add_data_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--symbol", required=True, help="标的代码，如 159920")
    p.add_argument("--start", type=_parse_date, required=True, help="起始日期 YYYY-MM-DD")
    p.add_argument("--end", type=_parse_date, required=True, help="结束日期 YYYY-MM-DD")
    p.add_argument(
        "--frame",
        choices=[f.value for f in Frame],
        default=Frame.DAILY.value,
        help="K 线周期",
    )
    p.add_argument("--refresh", action="store_true", help="强制重新下载，忽略缓存")


def _parse_date(text: str) -> date:
    return date.fromisoformat(text)


def _cmd_fetch(args: argparse.Namespace) -> int:
    frame = Frame(args.frame)
    series = load_bars(args.symbol, args.start, args.end, frame, refresh=args.refresh)
    if not series.bars:
        print(f"{args.symbol} 在 {args.start} ~ {args.end} 无数据")
        return 1
    print(
        f"已缓存 {args.symbol}（{args.frame}）：{len(series)} 根，"
        f"{series.bars[0].ts.date()} ~ {series.bars[-1].ts.date()}"
    )
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    frame = Frame(args.frame)
    config = _load_config(args.config)
    series = load_bars(args.symbol, args.start, args.end, frame, refresh=args.refresh)
    if not series.bars:
        print(f"{args.symbol} 在 {args.start} ~ {args.end} 无数据，无法回测")
        return 1
    result = simulate(config, series, initial_cash=args.initial_cash)
    print(render_summary(result, config))
    out_path = _write_report(render_report(result, config), args.out, args.symbol, args.frame)
    print(f"\n完整报告：{out_path}")
    return 0


def _load_config(path: Path) -> GridConfig:
    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return GridConfig.from_dict(data)


def _write_report(text: str, out_dir: Path, symbol: str, frame: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}_{frame}.md"
    path.write_text(text, encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(main())
