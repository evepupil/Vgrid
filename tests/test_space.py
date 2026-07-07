"""参数空间展开测试。"""

from decimal import Decimal

import pytest

from vgrid.scan.space import ScanSpec

_FIXED = {
    "symbol": "159920",
    "lower_price": "1.00",
    "upper_price": "1.20",
    "per_grid_amount": "2000",
    "capital_cap": "50000",
}


def test_size_is_cartesian_product() -> None:
    spec = ScanSpec(
        fixed=_FIXED,
        vary={"grid_count": [4, 6, 8], "spacing_mode": ["arithmetic", "geometric"]},
    )
    assert spec.size == 6


def test_expand_size_and_legit_config() -> None:
    spec = ScanSpec(
        fixed=_FIXED,
        vary={"grid_count": [4, 6, 8], "spacing_mode": ["arithmetic", "geometric"]},
    )
    configs = spec.expand()
    assert len(configs) == 6
    for c in configs:
        assert c.symbol == "159920"
        assert c.grid_count in {4, 6, 8}


def test_expand_inherits_fixed() -> None:
    spec = ScanSpec(fixed=_FIXED, vary={"grid_count": [4, 8]})
    for c in spec.expand():
        assert c.capital_cap == Decimal("50000")
        assert c.lower_price == Decimal("1.00")


def test_expand_applies_vary_values() -> None:
    spec = ScanSpec(
        fixed=_FIXED,
        vary={"grid_count": [4, 8], "spacing_mode": ["arithmetic", "geometric"]},
    )
    combos = {(c.grid_count, c.spacing_mode.value) for c in spec.expand()}
    assert combos == {
        (4, "arithmetic"),
        (4, "geometric"),
        (8, "arithmetic"),
        (8, "geometric"),
    }


def test_to_dict_from_dict_roundtrip() -> None:
    spec = ScanSpec(fixed={"symbol": "159920"}, vary={"grid_count": [4, 8]})
    restored = ScanSpec.from_dict(spec.to_dict())
    assert restored.fixed == {"symbol": "159920"}
    assert restored.vary == {"grid_count": [4, 8]}


def test_empty_vary_rejected() -> None:
    with pytest.raises(ValueError, match="至少扫一个字段"):
        ScanSpec(fixed=_FIXED, vary={})


def test_empty_candidate_list_rejected() -> None:
    with pytest.raises(ValueError, match="候选值列表不能为空"):
        ScanSpec(fixed=_FIXED, vary={"grid_count": []})


def test_too_many_combos_rejected() -> None:
    spec = ScanSpec(fixed=_FIXED, vary={"grid_count": list(range(5001))})
    with pytest.raises(ValueError, match="超过上限"):
        spec.expand()


def test_unknown_vary_field_rejected() -> None:
    # 拼错字段名（grid_counts），旧实现会被 from_dict 静默丢弃、无声失效
    with pytest.raises(ValueError, match="未知的 GridConfig 字段"):
        ScanSpec(fixed=_FIXED, vary={"grid_counts": [4, 8]})


def test_unknown_fixed_field_rejected() -> None:
    with pytest.raises(ValueError, match="未知的 GridConfig 字段"):
        ScanSpec(fixed={**_FIXED, "grd_count": 4}, vary={"grid_count": [4, 8]})


def test_fixed_vary_overlap_rejected() -> None:
    with pytest.raises(ValueError, match="同时出现在 fixed 和 vary"):
        ScanSpec(fixed={**_FIXED, "grid_count": 4}, vary={"grid_count": [4, 8]})


def test_vary_candidates_deduped() -> None:
    spec = ScanSpec(fixed=_FIXED, vary={"grid_count": [4, 4, 6]})
    assert spec.vary["grid_count"] == [4, 6]  # 重复值去掉，保持顺序
    assert spec.size == 2
    assert len(spec.expand()) == 2
