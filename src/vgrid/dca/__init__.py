"""dca —— 量化定投策略：日程 + 金额规则 + 回测引擎。纯逻辑，不碰 I/O。

第一版三种规则：固定金额、跌幅加码、均线偏离，只做离线回测和对比。
"""

from vgrid.dca.config import (
    AmountMode,
    AmountPolicy,
    DcaConfig,
    DrawdownTier,
    Frequency,
)
from vgrid.dca.engine import run_dca
from vgrid.dca.result import DcaMetrics, DcaResult, DcaTrade, SkippedBuy

__all__ = [
    "AmountMode",
    "AmountPolicy",
    "DcaConfig",
    "DcaMetrics",
    "DcaResult",
    "DcaTrade",
    "DrawdownTier",
    "Frequency",
    "SkippedBuy",
    "run_dca",
]
