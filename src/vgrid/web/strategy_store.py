"""策略库：``strategies/`` 目录下策略 JSON 的 CRUD（纯逻辑 + 文件 I/O）。

策略文件 ``<name>.json``，内容是 ``GridConfig.to_dict()`` 格式。name 限字母数字中文
下划线横线（1~64 字），杜绝路径穿越。读写都过 ``GridConfig.from_dict`` 校验合法性——
坏文件在 list 时跳过，单读抛错。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from vgrid.core.config import GridConfig

_NAME_RE = re.compile(r"^[A-Za-z0-9_\-一-龥]{1,64}$")


@dataclass(frozen=True, slots=True)
class StrategySummary:
    """策略列表项摘要（不带完整参数，列表展示用）。"""

    name: str
    symbol: str
    spacing_mode: str
    base_build_mode: str
    grid_count: int
    lower_price: str
    upper_price: str


def list_strategies(base: Path) -> list[StrategySummary]:
    """列出 base 目录下所有合法策略，按 name 排序。坏文件跳过。"""
    if not base.exists():
        return []
    summaries: list[StrategySummary] = []
    for path in sorted(base.glob("*.json")):
        name = path.stem
        if not _NAME_RE.match(name):
            continue
        try:
            cfg = _load(path)
        except (ValueError, OSError):
            continue
        summaries.append(_summary(name, cfg))
    return summaries


def read_strategy(base: Path, name: str) -> dict[str, object]:
    """读单个策略（规范化后的 ``to_dict``）。

    name 非法抛 ``ValueError``，不存在抛 ``FileNotFoundError``。
    """
    _require_valid_name(name)
    path = base / f"{name}.json"
    return _load(path).to_dict()


def write_strategy(base: Path, name: str, data: dict[str, object]) -> None:
    """新建 / 覆盖策略。先 ``GridConfig.from_dict`` 校验合法性，再落盘。"""
    _require_valid_name(name)
    cfg = GridConfig.from_dict(data)
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{name}.json"
    path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def delete_strategy(base: Path, name: str) -> bool:
    """删除策略。不存在返回 False（幂等）。"""
    _require_valid_name(name)
    path = base / f"{name}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _require_valid_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise ValueError(f"策略名非法：{name!r}（仅限字母数字中文下划线横线，1~64 字）")


def _load(path: Path) -> GridConfig:
    if not path.exists():
        raise FileNotFoundError(f"策略不存在：{path.stem}")
    with path.open(encoding="utf-8") as fh:
        loaded: dict[str, object] = json.load(fh)
    return GridConfig.from_dict(loaded)


def _summary(name: str, cfg: GridConfig) -> StrategySummary:
    return StrategySummary(
        name=name,
        symbol=cfg.symbol,
        spacing_mode=cfg.spacing_mode.value,
        base_build_mode=cfg.base_build_mode.value,
        grid_count=cfg.grid_count,
        lower_price=str(cfg.lower_price),
        upper_price=str(cfg.upper_price),
    )
