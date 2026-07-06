"""etf_info 缓存测试（mock ak 不打网）。"""

from __future__ import annotations

import pandas as pd
import pytest

from vgrid.web.etf_info import EtfInfoCache


def test_get_name(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = EtfInfoCache()
    df = pd.DataFrame({"代码": ["159920", "510300"], "名称": ["恒生ETF", "沪深300ETF"]})
    monkeypatch.setattr("vgrid.web.etf_info.ak.fund_etf_spot_em", lambda: df)
    assert cache.get_name("159920") == "恒生ETF"
    assert cache.get_name("510300") == "沪深300ETF"
    assert cache.get_name("000000") is None


def test_cache_reuses(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = EtfInfoCache()
    calls = {"n": 0}

    def _fake() -> pd.DataFrame:
        calls["n"] += 1
        return pd.DataFrame({"代码": ["159920"], "名称": ["恒生ETF"]})

    monkeypatch.setattr("vgrid.web.etf_info.ak.fund_etf_spot_em", _fake)
    cache.get_name("159920")
    cache.get_name("159920")
    assert calls["n"] == 1  # 第二次走缓存
