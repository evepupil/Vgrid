"""网格阶梯 API 逻辑：config+price → 预览视图，及视图转 JSON 安全 dict（纯逻辑，单测重点）。

``preview_ladder`` 用给定 config 在某价位建一条阶梯（``start`` 按建仓模式布局），
不依赖任何实例历史——展示这套参数在该价位下「会长成什么样」。``ladder_to_dict``
被预览端点和 ``/api/state`` 共用，序列化口径一处定义。
"""

from __future__ import annotations

from decimal import Decimal

from vgrid.core.config import GridConfig
from vgrid.strategy.engine import GridEngine
from vgrid.strategy.ladder_view import LadderView, build_ladder_view


def preview_ladder(config: GridConfig, price: Decimal) -> dict[str, object]:
    """按 config 在 ``price`` 处建一条阶梯，返回结构化视图 dict。"""
    engine = GridEngine(config)
    engine.start(price)
    return ladder_to_dict(build_ladder_view(engine, price))


def ladder_to_dict(view: LadderView) -> dict[str, object]:
    """``LadderView`` → JSON 安全 dict（``Decimal`` 转 ``str`` 保精度）。"""
    return {
        "current_price": str(view.current_price),
        "cap_price": str(view.cap_price) if view.cap_price is not None else None,
        "window_lower": str(view.window_lower),
        "window_upper": str(view.window_upper),
        "step": str(view.step),
        "grid_count": view.grid_count,
        "spacing_mode": view.spacing_mode,
        "rungs": [
            {
                "price": str(r.price),
                "depth": r.depth,
                "kind": r.kind,
                "held_shares": r.held_shares,
            }
            for r in view.rungs
        ],
    }
