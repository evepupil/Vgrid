"""vgrid 命令行：回测 / 取数 / 扫描 / 定投 / 模拟盘。

子命令：
- ``vgrid fetch``    只下载行情并写入本地缓存（预热 / 调试）。
- ``vgrid backtest`` 下载行情 → 跑网格回测 → 终端摘要 + Markdown 报告。
- ``vgrid dca``      下载行情 → 跑量化定投回测 → 终端摘要 + Markdown 报告。
- ``vgrid scan``     网格搜索参数扫描。
- ``vgrid paper``    模拟盘（run / status / serve）。

策略参数走 ``--config <cfg.json>``（网格是 GridConfig、定投是 DcaConfig 的 to_dict 格式）；
数据区间、标的、周期走命令行参数。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from vgrid.backtest import simulate
from vgrid.core.config import GridConfig
from vgrid.core.enums import Frame
from vgrid.data import load_bars
from vgrid.dca import DcaConfig, run_dca
from vgrid.notify import make_notifier
from vgrid.paper import MootdxRealtimeProvider, PaperRunner
from vgrid.report import render_dca_report, render_dca_summary, render_report, render_summary
from vgrid.scan import ScanSpec, rank, render_scan_report, run_scan
from vgrid.store import connect, load_config
from vgrid.web import create_app

#: 已知可预期的异常：配置缺字段（KeyError）、校验 / JSON 解析失败（ValueError）、
#: 文件缺失 / 网络中断（OSError，requests 异常也归此类）。这些打一行人话就退 1；
#: 其余未预期异常放行 traceback，方便定位真 bug。
_KNOWN_ERRORS = (ValueError, KeyError, OSError)


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "paper":
        return _cmd_paper(args)  # paper 各子命令自带长驻 / 异常处理，不走 _guard
    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "fetch": _cmd_fetch,
        "dca": _cmd_dca,
        "scan": _cmd_scan,
        "backtest": _cmd_backtest,
    }
    return _guard(handlers[args.command], args)


def _cmd_paper(args: argparse.Namespace) -> int:
    if args.paper_command == "run":
        return _cmd_paper_run(args)
    if args.paper_command == "serve":
        return _cmd_paper_serve(args)
    return _cmd_paper_status(args)


def _guard(fn: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> int:
    """跑命令，把已知异常收成一行人话错误 + 退出码 1，未预期异常放行。"""
    try:
        return fn(args)
    except _KNOWN_ERRORS as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


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

    p_dca = sub.add_parser("dca", help="下载行情 → 跑定投回测 → 输出报告")
    _add_data_args(p_dca)
    p_dca.add_argument("--config", type=Path, required=True, help="定投配置 JSON（DcaConfig）")
    p_dca.add_argument("--out", type=Path, default=Path("reports"), help="报告输出目录")

    p_scan = sub.add_parser("scan", help="网格搜索参数扫描")
    _add_data_args(p_scan)
    p_scan.add_argument("--spec", type=Path, required=True, help="扫描规格 JSON（fixed + vary）")
    p_scan.add_argument(
        "--metric",
        choices=["sharpe", "total_return", "annualized_return", "calmar"],
        default="sharpe",
        help="排序指标",
    )
    p_scan.add_argument("--top", type=int, default=10, help="终端 / 报告展示的 top-N")
    p_scan.add_argument("--out", type=Path, default=Path("reports"), help="报告输出目录")
    p_scan.add_argument(
        "--initial-cash",
        type=Decimal,
        default=None,
        help="初始资金（默认用配置的 capital_cap）",
    )

    p_paper = sub.add_parser("paper", help="模拟盘（实时轮询 + 虚拟账户）")
    paper_sub = p_paper.add_subparsers(dest="paper_command", required=True)

    p_run = paper_sub.add_parser("run", help="启动模拟盘长驻轮询")
    p_run.add_argument("--config", type=Path, required=True, help="策略配置 JSON")
    p_run.add_argument("--symbol", required=True, help="标的代码")
    p_run.add_argument(
        "--db", type=Path, default=None, help="SQLite 库路径（默认 ~/.vgrid/paper.sqlite）"
    )
    p_run.add_argument("--interval", type=float, default=15.0, help="轮询间隔秒")
    p_run.add_argument(
        "--notify",
        choices=["serverchan", "pushplus"],
        default=None,
        help="网格触发推送通道（半自动实盘，只通知不下单；凭证走环境变量）",
    )

    p_status = paper_sub.add_parser("status", help="查看模拟盘当前状态")
    p_status.add_argument(
        "--db", type=Path, default=None, help="SQLite 库路径（默认 ~/.vgrid/paper.sqlite）"
    )

    p_serve = paper_sub.add_parser("serve", help="启动看盘 Web 面板")
    p_serve.add_argument(
        "--db", type=Path, default=None, help="SQLite 库路径（默认 ~/.vgrid/paper.sqlite）"
    )
    p_serve.add_argument("--host", default="127.0.0.1", help="监听地址")
    p_serve.add_argument("--port", type=int, default=8000, help="监听端口")
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


def _cmd_dca(args: argparse.Namespace) -> int:
    frame = Frame(args.frame)
    config = DcaConfig.from_dict(_load_json(args.config))
    series = load_bars(args.symbol, args.start, args.end, frame, refresh=args.refresh)
    if not series.bars:
        print(f"{args.symbol} 在 {args.start} ~ {args.end} 无数据，无法回测")
        return 1
    result = run_dca(config, series)
    print(render_dca_summary(result, config))
    report = render_dca_report(result, config)
    out_path = _write_report(report, args.out, f"{args.symbol}_dca", args.frame)
    print(f"\n完整报告：{out_path}")
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    frame = Frame(args.frame)
    spec = ScanSpec.from_dict(_load_json(args.spec))
    bars = load_bars(args.symbol, args.start, args.end, frame, refresh=args.refresh)
    if not bars.bars:
        print(f"{args.symbol} 在 {args.start} ~ {args.end} 无数据，无法扫描")
        return 1

    configs = spec.expand()

    def _progress(done: int, total: int) -> None:
        if done == total or done % 25 == 0:
            print(f"  已扫描 {done}/{total} 组…", file=sys.stderr)

    rows = run_scan(configs, bars, initial_cash=args.initial_cash, progress=_progress)
    ranked = rank(rows, args.metric)
    top = max(0, min(args.top, len(ranked)))  # 钳制下界，负数不再切出错误切片
    best = ranked[0]
    best_result = simulate(best.config, bars, initial_cash=args.initial_cash)

    print(f"扫描完成：{len(rows)} 组，按 `{args.metric}` 排序前 {top}：\n")
    print(render_scan_report(ranked, args.metric, top, spec))
    print("最优组合：")
    print(render_summary(best_result, best.config))

    scan_path = _write_report(
        render_scan_report(ranked, args.metric, len(ranked), spec),
        args.out,
        f"scan_{args.symbol}",
        args.frame,
    )
    best_path = _write_report(
        render_report(best_result, best.config),
        args.out,
        f"best_{args.symbol}",
        args.frame,
    )
    print(f"\n扫描报告：{scan_path}")
    print(f"最优组合完整报告：{best_path}")
    return 0


def _default_db() -> Path:
    """默认模拟盘库：~/.vgrid/paper.sqlite。"""
    return Path.home() / ".vgrid" / "paper.sqlite"


def _cmd_paper_run(args: argparse.Namespace) -> int:
    db = args.db or _default_db()
    config = _load_config(args.config)
    notifier = None
    if args.notify:
        try:
            notifier = make_notifier(args.notify)
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            return 1
    conn = connect(str(db))
    runner = PaperRunner(
        config, MootdxRealtimeProvider(), conn, interval=args.interval, notifier=notifier
    )
    print(f"模拟盘启动 · {args.symbol}（库 {db}，轮询 {args.interval}s）")
    if notifier is not None:
        print(f"  推送：{args.notify}（半自动，只通知不下单）")
    print("—— Ctrl+C 停止，重启 replay 续跑")
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        conn.close()
    return 0


def _cmd_paper_status(args: argparse.Namespace) -> int:
    db = args.db or _default_db()
    if not db.exists():
        print(f"库不存在：{db}，先 paper run")
        return 1
    conn = connect(str(db))
    config = load_config(conn)
    if config is None:
        print(f"库 {db} 无模拟盘数据，先 paper run")
        conn.close()
        return 1
    runner = PaperRunner(config, MootdxRealtimeProvider(), conn)
    runner.replay()
    snap = runner.snapshot()
    print(f"模拟盘状态 · {config.symbol}（库 {db}）")
    print(f"  最新价: {snap.last_price}  时间: {snap.last_ts}")
    print(f"  持仓: {snap.open_lots} 格  占用资金: {snap.committed}")
    print(f"  已实现盈亏: {snap.realized_pnl}  手续费: {snap.total_fee}")
    print(f"  净现金流: {snap.cash_flow}  成交: {snap.n_fills} 笔")
    conn.close()
    return 0


def _cmd_paper_serve(args: argparse.Namespace) -> int:
    import uvicorn  # noqa: PLC0415  懒导入，避免 cli 模块加载依赖 uvicorn

    db = args.db or _default_db()
    app = create_app(str(db), frontend_dist=Path("frontend/dist"))
    print(f"看盘面板启动 · http://{args.host}:{args.port}（库 {db}）")
    print("—— Ctrl+C 停止")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded: dict[str, Any] = json.load(fh)
    return loaded


def _load_config(path: Path) -> GridConfig:
    return GridConfig.from_dict(_load_json(path))


def _write_report(text: str, out_dir: Path, symbol: str, frame: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}_{frame}.md"
    path.write_text(text, encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(main())
