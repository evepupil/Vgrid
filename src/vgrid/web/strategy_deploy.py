"""策略库增强 + 部署（FR-9.2 / 9.3）。

**增强**：把 ``strategies/`` 里的策略与 ``paper/`` 里的运行实例交叉引用——实例名 = 策略名
即视为「已部署」，带出状态（运行/停歇/草稿）+ 该实例夏普 + 关联实例名。

**部署**：把一条策略落成一个模拟盘实例——在 ``paper/<name>.sqlite`` 写入策略 config
（``save_config``），实例随即出现在组合总览（停歇态，等 runner 喂 tick）。真正开始跟盘的
长驻轮询仍走 ``vgrid paper run`` CLI（与「启停走 CLI」的既有架构一致），响应里回好可直接
复制的启动命令。实盘执行（真实下单）是后续 slice，当前 live/sim 都落到模拟盘库。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vgrid.core.config import GridConfig
from vgrid.store.db import connect
from vgrid.store.repository import load_config, save_config
from vgrid.web.strategy_store import list_strategies, read_strategy


@dataclass(frozen=True, slots=True)
class InstanceRef:
    """部署后关联的运行实例（组合层给的最小信息）。"""

    name: str
    status: str  # running / idle
    sharpe: str  # 该实例回放算出的夏普（字符串保精度）


@dataclass(frozen=True, slots=True)
class EnrichedStrategy:
    """策略 + 部署状态（FR-9.2）。"""

    name: str
    symbol: str
    spacing_mode: str
    base_build_mode: str
    grid_count: int
    lower_price: str
    upper_price: str
    status: str  # draft（未部署）/ running（实例在跑）/ idle（已部署但停歇）
    instance_name: str | None  # 关联实例名，未部署为 None
    sharpe: str | None  # 关联实例夏普，未部署为 None


@dataclass(frozen=True, slots=True)
class DeployResult:
    """部署结果。"""

    instance_name: str
    db_path: str
    symbol: str
    mode: str
    start_command: str  # 开始跟盘的 CLI 命令，可直接复制


def enrich_strategies(
    strategies_dir: Path, instances: dict[str, InstanceRef]
) -> list[EnrichedStrategy]:
    """列策略 + 交叉引用实例（``instances`` 键为实例名）。实例名 == 策略名 视作已部署。"""
    out: list[EnrichedStrategy] = []
    for s in list_strategies(strategies_dir):
        inst = instances.get(s.name)
        if inst is None:
            status, instance_name, sharpe = "draft", None, None
        else:
            status, instance_name, sharpe = inst.status, inst.name, inst.sharpe
        out.append(
            EnrichedStrategy(
                name=s.name,
                symbol=s.symbol,
                spacing_mode=s.spacing_mode,
                base_build_mode=s.base_build_mode,
                grid_count=s.grid_count,
                lower_price=s.lower_price,
                upper_price=s.upper_price,
                status=status,
                instance_name=instance_name,
                sharpe=sharpe,
            )
        )
    return out


def deploy_strategy(
    strategies_dir: Path, paper_dir: Path, name: str, *, mode: str = "sim"
) -> DeployResult:
    """把策略 ``name`` 落成 ``paper/<name>.sqlite`` 实例（写入 config）。

    已存在同名实例则抛 ``FileExistsError``（已部署，别重复建）。策略不存在抛
    ``FileNotFoundError``（由 ``read_strategy`` 抛）。
    """
    config_dict = read_strategy(strategies_dir, name)  # 不存在会抛，且已过合法性校验
    config = GridConfig.from_dict(config_dict)

    paper_dir.mkdir(parents=True, exist_ok=True)
    db_path = paper_dir / f"{name}.sqlite"
    # 检查 + 写入放同一连接，且用 BEGIN IMMEDIATE 立即拿写锁（review #32）——
    # 原先 exists()+load_config 与后面的 connect+save_config 是两段连接周期、无锁，
    # 两个并发部署都能过检查同时写入。现在第二个会卡在 BEGIN，等首个提交后读到 config 再抛。
    conn = connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = load_config(conn)
        if existing is not None:
            conn.rollback()
            raise FileExistsError(f"策略已部署为实例：{name}")
        save_config(conn, config)
    finally:
        conn.close()

    strategy_json = strategies_dir / f"{name}.json"
    start_command = (
        f"vgrid paper run --db {db_path} --config {strategy_json} --symbol {config.symbol}"
    )
    return DeployResult(
        instance_name=name,
        db_path=str(db_path),
        symbol=config.symbol,
        mode=mode,
        start_command=start_command,
    )
