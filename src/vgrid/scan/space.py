"""参数扫描空间：固定字段 + 扫描字段，笛卡尔积展开成 GridConfig 列表。

扫描规格用「dict 字段名 → 值」表达，展开时统一走 ``GridConfig.from_dict``，``Decimal`` /
枚举的转换全复用 ``GridConfig`` 已有的逻辑，不另写一套。这样 ``vary`` 里给
``grid_count: [4, 6, 8]`` 或 ``spacing_mode: ["arithmetic", "geometric"]`` 都能直接展开。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from itertools import product
from typing import Any

from vgrid.core.config import GridConfig

_MAX_COMBOS = 5000  # 组合数硬上限，防止误跑爆栈

#: GridConfig 的合法字段名集合，用于校验 fixed / vary 的键，挡住拼错的字段名。
_CONFIG_FIELDS = frozenset(f.name for f in fields(GridConfig))


def _dedup_preserve_order(vals: list[Any]) -> list[Any]:
    """按出现顺序去重。可哈希值走 dict.fromkeys（O(n)），不可哈希退回线性比较。"""
    try:
        return list(dict.fromkeys(vals))
    except TypeError:
        out: list[Any] = []
        for v in vals:
            if v not in out:
                out.append(v)
        return out


@dataclass(frozen=True, slots=True)
class ScanSpec:
    """参数扫描规格。

    Attributes:
        fixed: 固定的 GridConfig 字段（如 symbol / 区间 / 资金上限）。
        vary: 要扫描的字段 → 候选值列表；展开时做笛卡尔积。
    """

    fixed: Mapping[str, Any]
    vary: Mapping[str, list[Any]]

    def __post_init__(self) -> None:
        if not self.vary:
            raise ValueError("vary 不能为空（至少扫一个字段）")

        # 校验字段名合法——拼错的字段（如 grid_counts）会被 from_dict 静默丢弃，
        # 导致该维度无声失效、产出重复 config，甚至渲染时 getattr 崩，必须挡在源头。
        unknown = sorted({*self.fixed, *self.vary} - _CONFIG_FIELDS)
        if unknown:
            raise ValueError(
                f"未知的 GridConfig 字段：{unknown}；合法字段：{sorted(_CONFIG_FIELDS)}"
            )

        # 同名字段同时出现在 fixed 和 vary 会让 vary 无声盖掉 fixed，行为反直觉。
        overlap = sorted(set(self.fixed) & set(self.vary))
        if overlap:
            raise ValueError(f"字段同时出现在 fixed 和 vary：{overlap}，请只留一处")

        # 候选值去重（重复值会产出重复 config、size 虚高、报告出重复行）。
        deduped: dict[str, list[Any]] = {}
        for key, vals in self.vary.items():
            if not vals:
                raise ValueError(f"vary[{key!r}] 候选值列表不能为空")
            deduped[key] = _dedup_preserve_order(list(vals))
        object.__setattr__(self, "vary", deduped)

    @property
    def size(self) -> int:
        """组合数 = Π len(vary[k])。"""
        n = 1
        for vals in self.vary.values():
            n *= len(vals)
        return n

    def expand(self) -> tuple[GridConfig, ...]:
        """笛卡尔积展开成具体 GridConfig 列表。"""
        if self.size > _MAX_COMBOS:
            raise ValueError(f"参数组合数 {self.size} 超过上限 {_MAX_COMBOS}，请收窄 vary")
        keys = list(self.vary)
        configs: list[GridConfig] = []
        for combo in product(*(self.vary[k] for k in keys)):
            data: dict[str, Any] = dict(self.fixed)
            for k, v in zip(keys, combo, strict=True):
                data[k] = v
            configs.append(GridConfig.from_dict(data))
        return tuple(configs)

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的 dict（fixed / vary 的值应为 JSON 原生类型）。"""
        return {"fixed": dict(self.fixed), "vary": dict(self.vary)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScanSpec:
        """从 dict 反序列化（``to_dict`` 的逆操作）。"""
        fixed = data.get("fixed", {})
        if not isinstance(fixed, Mapping):
            raise ValueError("fixed 必须是对象")
        vary = data.get("vary", {})
        if not isinstance(vary, Mapping):
            raise ValueError("vary 必须是对象")
        return cls(fixed=dict(fixed), vary=dict(vary))
