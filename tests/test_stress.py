"""黑天鹅推演纯函数测试：占用/兜底、逐档下跌浮亏、放大区、最大占用。"""

from __future__ import annotations

from decimal import Decimal

from vgrid.analysis.stress import StressReport, black_swan_report


def _report(**kw: Decimal) -> StressReport:
    base: dict[str, Decimal] = {
        "current_price": Decimal("1.10"),
        "position_value": Decimal("10000"),
        "unrealized": Decimal("200"),
        "committed": Decimal("5000"),
        "capital_cap": Decimal("50000"),
        "lower_price": Decimal("1.00"),
        "down_spacing_factor": Decimal("1"),
        "down_amount_factor": Decimal("1"),
    }
    base.update(kw)
    return black_swan_report(
        current_price=base["current_price"],
        position_value=base["position_value"],
        unrealized=base["unrealized"],
        committed=base["committed"],
        capital_cap=base["capital_cap"],
        lower_price=base["lower_price"],
        down_spacing_factor=base["down_spacing_factor"],
        down_amount_factor=base["down_amount_factor"],
    )


def test_occupancy_ratio_and_buffer() -> None:
    r = _report(committed=Decimal("5000"), capital_cap=Decimal("50000"))
    assert r.occupancy.ratio_pct == Decimal("10")
    assert r.occupancy.buffer_pct == Decimal("90")


def test_occupancy_zero_cap_guarded() -> None:
    r = _report(committed=Decimal("100"), capital_cap=Decimal("0"))
    assert r.occupancy.ratio_pct == Decimal("0")
    assert r.occupancy.buffer_pct == Decimal("100")


def test_scenarios_default_three_drops() -> None:
    r = _report()
    assert [s.drop_pct for s in r.scenarios] == [
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.20"),
    ]


def test_drop_loss_is_position_value_times_drop() -> None:
    r = _report(position_value=Decimal("10000"), unrealized=Decimal("200"))
    s10 = next(s for s in r.scenarios if s.drop_pct == Decimal("0.10"))
    assert s10.position_loss == Decimal("1000")  # 10000 × 10%
    assert s10.projected_unrealized == Decimal("-800")  # 200 − 1000
    assert s10.scenario_price == Decimal("0.99")  # 1.10 ×(1−0.10)


def test_amplification_disabled_when_factors_one() -> None:
    r = _report(down_spacing_factor=Decimal("1"), down_amount_factor=Decimal("1"))
    assert r.amplification.enabled is False
    assert "未启用放大区" in r.amplification.note


def test_amplification_enabled_when_factor_gt_one() -> None:
    r = _report(down_spacing_factor=Decimal("1.5"), down_amount_factor=Decimal("1"))
    assert r.amplification.enabled is True
    assert "1.5" in r.amplification.note
    assert r.amplification.lower_price == Decimal("1.00")


def test_max_occupancy_is_capital_cap() -> None:
    r = _report(capital_cap=Decimal("50000"))
    assert r.max_occupancy == Decimal("50000")
