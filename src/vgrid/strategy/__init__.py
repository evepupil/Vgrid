"""strategy —— 网格策略层。纯逻辑状态机，不碰任何 I/O。

回测和模拟盘共用同一份策略引擎，杜绝「回测一套、实盘另一套」的偏差。
"""

from vgrid.strategy.engine import GridEngine
from vgrid.strategy.gridlines import (
    bottom_gap,
    build_levels,
    shift_window_up,
)
from vgrid.strategy.ladder import GridLine, Ladder
from vgrid.strategy.ladder_view import LadderRung, LadderView, build_ladder_view

__all__ = [
    "GridEngine",
    "GridLine",
    "Ladder",
    "LadderRung",
    "LadderView",
    "bottom_gap",
    "build_ladder_view",
    "build_levels",
    "shift_window_up",
]
