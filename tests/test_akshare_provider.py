"""akshare provider：列适配 + fetch（mock akshare，不打网）。"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from vgrid.core.enums import Frame
from vgrid.data.akshare_provider import AkshareProvider, _df_to_columns


def _sample_df() -> pd.DataFrame:
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


def test_df_to_columns_maps_chinese_headers() -> None:
    cols = _df_to_columns(_sample_df(), ts_col="日期")
    assert cols["ts"] == ["2024-01-02", "2024-01-03"]
    assert cols["open"] == [1.00, 1.01]
    assert cols["close"] == [1.03, 1.04]


def test_df_to_columns_rejects_missing_column() -> None:
    df = pd.DataFrame({"日期": ["2024-01-02"], "开盘": [1.0]})
    with pytest.raises(ValueError, match="缺少列"):
        _df_to_columns(df, ts_col="日期")


def test_fetch_daily_through_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _sample_df()
    captured: dict[str, object] = {}

    def _fake_hist(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return df

    monkeypatch.setattr("vgrid.data.akshare_provider.ak.fund_etf_hist_em", _fake_hist)
    prov = AkshareProvider()
    series = prov.fetch("159920", date(2024, 1, 2), date(2024, 1, 3), Frame.DAILY)

    assert captured["symbol"] == "159920"
    assert captured["start_date"] == "20240102"
    assert captured["end_date"] == "20240103"
    assert len(series) == 2
    assert series[0].open == Decimal("1.00")
    assert series[1].close == Decimal("1.04")
    assert series[0].ts.date() == date(2024, 1, 2)
