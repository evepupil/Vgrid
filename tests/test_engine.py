"""网格引擎状态机测试。"""

from collections.abc import Callable
from decimal import Decimal

from vgrid.core import GridConfig, Side
from vgrid.core.enums import BaseBuildMode
from vgrid.strategy import GridEngine

MakeConfig = Callable[..., GridConfig]


def test_zero_start_no_fills(make_config: MakeConfig) -> None:
    engine = GridEngine(make_config(base_build_mode=BaseBuildMode.ZERO))
    assert engine.start(Decimal("1.10")) == []
    assert engine.open_lots == 0


def test_single_round_trip_profit(make_config: MakeConfig) -> None:
    """跌一格买、涨回来卖，赚一格差价，两边各扣手续费。"""
    engine = GridEngine(make_config(base_build_mode=BaseBuildMode.ZERO))
    engine.start(Decimal("1.15"))

    buys = engine.step(Decimal("1.10"))
    assert len(buys) == 1
    assert buys[0].side is Side.BUY
    assert buys[0].price == Decimal("1.10")
    assert buys[0].shares == 1800  # floor(2000/1.10) 取整到手

    sells = engine.step(Decimal("1.15"))
    assert len(sells) == 1
    assert sells[0].side is Side.SELL
    assert sells[0].price == Decimal("1.15")

    # 买 1800 份 @1.10 花 1980.10（含费 0.10），卖 @1.15 得 2069.90（含费 0.10）
    assert engine.realized_pnl == Decimal("89.80")
    assert engine.total_fee == Decimal("0.20")
    assert engine.open_lots == 0
    # 平仓后净现金流应等于已实现盈亏（守恒）
    assert engine.cash_flow == engine.realized_pnl


def test_center_start_builds_upper_inventory(make_config: MakeConfig) -> None:
    engine = GridEngine(make_config())  # 默认中枢建仓
    fills = engine.start(Decimal("1.10"))

    # 现价上方两个格子（目标 1.15、1.20）各买一份底仓
    assert len(fills) == 2
    assert all(f.side is Side.BUY for f in fills)
    targets = {lot.sell_target for lot in engine.open_positions}
    assert targets == {Decimal("1.150"), Decimal("1.200")}

    # 涨到 1.20，两份底仓全部止盈
    engine.step(Decimal("1.20"))
    assert engine.open_lots == 0
    assert engine.realized_pnl > 0


def test_capital_cap_stops_buying(make_config: MakeConfig) -> None:
    engine = GridEngine(
        make_config(base_build_mode=BaseBuildMode.ZERO, capital_cap=Decimal("4000"))
    )
    engine.start(Decimal("1.20"))
    engine.step(Decimal("1.00"))  # 一路跌到底

    # 资金上限 4000 只够买两格，更低的格子不再买
    assert engine.open_lots == 2
    assert engine.committed <= Decimal("4000")


def test_downward_extension_buys_with_widened_grid(make_config: MakeConfig) -> None:
    engine = GridEngine(
        make_config(
            base_build_mode=BaseBuildMode.ZERO,
            down_spacing_factor=Decimal("2"),
        )
    )
    engine.start(Decimal("1.00"))  # 从基准下沿起步
    engine.step(Decimal("0.80"))  # 跌破下沿，触发向下延伸

    # 延伸出的买点在 0.95、0.85（间距 0.05 → 0.10 放大），各买一份
    buy_prices = {lot.buy_price for lot in engine.open_positions}
    assert buy_prices == {Decimal("0.950"), Decimal("0.850")}


def test_upper_breakout_shifts_without_rebuild(make_config: MakeConfig) -> None:
    engine = GridEngine(
        make_config(
            base_build_mode=BaseBuildMode.ZERO,
            upper_rebuild_ratio=Decimal("0"),
        )
    )
    engine.start(Decimal("1.00"))
    engine.step(Decimal("1.32"))  # 冲破上沿

    assert engine.ladder.top == Decimal("1.350")  # 网格已上移追踪
    assert engine.open_lots == 0  # ratio=0：只上移不追高重建


def test_upper_breakout_rebuilds_when_ratio_positive(make_config: MakeConfig) -> None:
    engine = GridEngine(
        make_config(
            base_build_mode=BaseBuildMode.ZERO,
            upper_rebuild_ratio=Decimal("1"),
        )
    )
    engine.start(Decimal("1.00"))
    engine.step(Decimal("1.32"))

    assert engine.ladder.top == Decimal("1.350")
    assert engine.open_lots == 1  # 立即按新中枢重建底仓
    lot = engine.open_positions[0]
    assert lot.buy_price == Decimal("1.32")
    assert lot.sell_target == Decimal("1.350")


def test_desired_orders_reflect_state(make_config: MakeConfig) -> None:
    engine = GridEngine(make_config())  # 中枢建仓
    engine.start(Decimal("1.10"))

    orders = engine.desired_orders(Decimal("1.10"))
    sells = [o for o in orders if o.side is Side.SELL]
    buys = [o for o in orders if o.side is Side.BUY]

    # 两份底仓 → 两个卖单；现价下方两条空线（1.05、1.00）→ 两个买单
    assert len(sells) == 2
    assert len(buys) == 2
    assert {o.price for o in buys} == {Decimal("1.050"), Decimal("1.000")}


def test_tight_cap_keeps_positions_contiguous(make_config: MakeConfig) -> None:
    """紧资金上限 + down_amount_factor<1：触及上限即停，不跳过去买更便宜的下格。

    回归 #1：曾用 continue，导致买出 {0.95, 0.85} 这种漏掉 0.90 的非连续持仓，
    且与 desired_orders 的 break 口径漂移。改 break 后只买到就近能买的一格。
    """
    engine = GridEngine(
        make_config(
            base_build_mode=BaseBuildMode.ZERO,
            down_amount_factor=Decimal("0.5"),
            down_spacing_factor=Decimal("1"),
            capital_cap=Decimal("1200"),
        )
    )
    engine.start(Decimal("1.00"))
    engine.step(Decimal("0.80"))

    buy_prices = {lot.buy_price for lot in engine.open_positions}
    assert buy_prices == {Decimal("0.950")}  # 只买到就近一格，没跳买更低的 0.85


def test_desired_orders_is_read_only(make_config: MakeConfig) -> None:
    """回归 #2：desired_orders 是只读查询，不能偷偷向下延伸阶梯。"""
    engine = GridEngine(make_config(base_build_mode=BaseBuildMode.ZERO))
    engine.start(Decimal("1.00"))
    before_bottom = engine.ladder.bottom
    before_len = len(engine.ladder.lines)

    engine.desired_orders(Decimal("0.80"))  # 远低于下沿，旧实现会在此永久延伸阶梯

    assert engine.ladder.bottom == before_bottom
    assert len(engine.ladder.lines) == before_len
