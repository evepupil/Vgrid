"""akshare provider：列适配 + fetch（mock akshare，不打网）。"""

from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from vgrid.core.enums import Frame
from vgrid.data.akshare_provider import AkshareProvider, _df_to_columns

_COL_MAP_EM = {"开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
_COL_MAP_SINA = {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}


def _sample_df_em() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "日期": ["2024-01-02", "2024-01-03"],
            "开盘": [1.00, 1.01],
            "最高": [1.05, 1.06],
            "最低": [0.99, 1.00],
            "收盘": [1.03, 1.04],
            "成交量": [100, 200],
        }
    )


def _sample_df_sina() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [1.00, 1.01, 1.02],
            "high": [1.05, 1.06, 1.07],
            "low": [0.99, 1.00, 1.01],
            "close": [1.03, 1.04, 1.05],
            "volume": [100, 200, 300],
        }
    )


def test_invalid_source_rejected() -> None:
    with pytest.raises(ValueError, match="不支持的 source"):
        AkshareProvider(source="xxx")


def test_df_to_columns_em_maps_chinese() -> None:
    cols = _df_to_columns(_sample_df_em(), ts_col="日期", col_map=_COL_MAP_EM)
    assert cols["ts"] == ["2024-01-02", "2024-01-03"]
    assert cols["close"] == [1.03, 1.04]


def test_df_to_columns_sina_identity() -> None:
    cols = _df_to_columns(_sample_df_sina(), ts_col="date", col_map=_COL_MAP_SINA)
    assert cols["ts"] == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert cols["open"] == [1.00, 1.01, 1.02]


def test_df_to_columns_rejects_missing_column() -> None:
    df = pd.DataFrame({"date": ["2024-01-02"], "open": [1.0]})
    with pytest.raises(ValueError, match="缺少列"):
        _df_to_columns(df, ts_col="date", col_map=_COL_MAP_SINA)


def test_fetch_daily_em_through_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _sample_df_em()
    captured: dict[str, object] = {}

    def _fake(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return df

    monkeypatch.setattr("vgrid.data.akshare_provider.ak.fund_etf_hist_em", _fake)
    prov = AkshareProvider(source="em")
    series = prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)

    assert captured["symbol"] == "159920"
    assert captured["start_date"] == "20240102"
    assert captured["end_date"] == "20240103"
    assert len(series) == 2
    assert series[0].open == Decimal("1.00")
    assert series[1].close == Decimal("1.04")
    assert series[0].ts.date() == date(2024, 1, 2)


def test_fetch_daily_sina_through_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认 sina 源：加 sz/sh 前缀，返回全量后按区间过滤。"""
    df = _sample_df_sina()  # 3 行，过滤后留 2 行
    captured: dict[str, object] = {}

    def _fake(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return df

    monkeypatch.setattr("vgrid.data.akshare_provider.ak.fund_etf_hist_sina", _fake)
    prov = AkshareProvider()  # 默认 sina
    series = prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)

    assert captured["symbol"] == "sz159920"  # 深市加 sz 前缀
    assert len(series) == 2  # 过滤掉 01-04
    assert series[0].open == Decimal("1.00")
    assert series[1].ts.date() == date(2024, 1, 3)


def test_fetch_daily_sina_sh_prefix_for_sh_etf(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _sample_df_sina()
    captured: dict[str, object] = {}

    def _fake(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return df

    monkeypatch.setattr("vgrid.data.akshare_provider.ak.fund_etf_hist_sina", _fake)
    prov = AkshareProvider()
    prov.fetch("510300", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)
    assert captured["symbol"] == "sh510300"  # 沪市加 sh 前缀


def _sample_df_min_em() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "时间": ["2024-01-02 09:31:00", "2024-01-02 09:32:00"],
            "开盘": [1.00, 1.01],
            "最高": [1.05, 1.06],
            "最低": [0.99, 1.00],
            "收盘": [1.03, 1.04],
            "成交量": [100, 200],
        }
    )


def test_fetch_minute_em_through_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """回归 #8：分钟线路径（东财 min_em，用「时间」列）此前零测试，这里锁住核心行为。"""
    df = _sample_df_min_em()
    captured: dict[str, object] = {}

    def _fake(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return df

    monkeypatch.setattr("vgrid.data.akshare_provider.ak.fund_etf_hist_min_em", _fake)
    prov = AkshareProvider()  # 分钟线不受 source 影响
    series = prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 2), Frame.MINUTE)

    assert captured["symbol"] == "159920"
    assert captured["period"] == "1"
    assert captured["start_date"] == "2024-01-02 09:30:00"
    assert captured["end_date"] == "2024-01-02 15:00:00"
    assert series.frame is Frame.MINUTE
    assert len(series) == 2
    assert series[0].ts == datetime(2024, 1, 2, 9, 31)  # 分钟时间戳解析到分
    assert series[1].close == Decimal("1.04")
