"""网格阶梯视图构造器测试。

用 make_config 默认区间 1.00~1.20、4 格等差 → 网格线 [1.00,1.05,1.10,1.15,1.20]。
"""

from collections.abc import Callable
from decimal import Decimal

from vgrid.core import GridConfig
from vgrid.core.enums import BaseBuildMode
from vgrid.strategy import GridEngine, build_ladder_view
from vgrid.strategy.ladder_view import KIND_BUY, KIND_CAPPED, KIND_IDLE, KIND_SELL

MakeConfig = Callable[..., GridConfig]


def _by_price(view: object) -> dict[Decimal, str]:
    return {r.price: r.kind for r in view.rungs}  # type: ignore[attr-defined]


def test_center_build_classifies_sell_and_buy(make_config: MakeConfig) -> None:
    """中枢建仓 @1.10：上方 1.15/1.20 是卖单格（有底仓），下方 1.05/1.00 是买单格。"""
    engine = GridEngine(make_config())  # 默认中枢建仓
    engine.start(Decimal("1.10"))
    view = build_ladder_view(engine, Decimal("1.10"))

    kinds = _by_price(view)
    assert kinds[Decimal("1.15")] == KIND_SELL
    assert kinds[Decimal("1.20")] == KIND_SELL
    assert kinds[Decimal("1.05")] == KIND_BUY
    assert kinds[Decimal("1.00")] == KIND_BUY
    assert kinds[Decimal("1.10")] == KIND_IDLE  # 现价那条，无底仓

    # 卖单格带持有份额，买单格不带
    held = {r.price: r.held_shares for r in view.rungs}
    assert held[Decimal("1.15")] > 0
    assert held[Decimal("1.05")] == 0

    assert view.cap_price is None  # 资金充裕，无排队
    assert view.window_lower == Decimal("1.00")
    assert view.window_upper == Decimal("1.20")
    assert view.step == Decimal("0.05")
    assert view.grid_count == 4
    assert view.spacing_mode == "arithmetic"


def test_capital_cap_produces_capped_rungs(make_config: MakeConfig) -> None:
    """资金上限很小：中枢只建得起最低一格底仓，下方买单被挡成排队格。"""
    engine = GridEngine(make_config(capital_cap=Decimal("2500")))
    engine.start(Decimal("1.10"))
    view = build_ladder_view(engine, Decimal("1.10"))

    kinds = _by_price(view)
    # 只建起 1.15 一格底仓（~1955 元 < 2500），1.20 因超上限没建 → 空闲
    assert kinds[Decimal("1.15")] == KIND_SELL
    assert kinds[Decimal("1.20")] == KIND_IDLE
    # 下方买单都被资金上限挡下 → 排队格
    assert kinds[Decimal("1.05")] == KIND_CAPPED
    assert kinds[Decimal("1.00")] == KIND_CAPPED
    # 资金上限触及价 = 最高一条排队格
    assert view.cap_price == Decimal("1.05")


def test_break_below_lower_extends_widening_zone(make_config: MakeConfig) -> None:
    """价格跌破下沿：阶梯向下延伸出放大区（depth>0），基准窗口不变。"""
    engine = GridEngine(make_config(base_build_mode=BaseBuildMode.ZERO))
    engine.start(Decimal("1.20"))
    engine.step(Decimal("0.80"))  # 跌破下沿 1.00，触发向下延伸
    view = build_ladder_view(engine, Decimal("0.80"))

    assert any(r.depth > 0 for r in view.rungs)  # 有放大区网格线
    assert any(r.price < Decimal("1.00") for r in view.rungs)
    assert view.window_lower == Decimal("1.00")  # 基准窗口下沿不变
    assert view.window_upper == Decimal("1.20")


def test_shift_up_moves_window(make_config: MakeConfig) -> None:
    """价格冲破上沿：窗口整体上移，视图窗口跟着变。"""
    engine = GridEngine(make_config(base_build_mode=BaseBuildMode.ZERO))
    engine.start(Decimal("1.10"))
    engine.step(Decimal("1.40"))  # 冲破上沿 1.20
    view = build_ladder_view(engine, Decimal("1.40"))

    assert view.window_upper > Decimal("1.20")  # 窗口已上移
    assert view.window_lower > Decimal("1.00")
