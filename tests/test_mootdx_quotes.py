"""mootdx 实时报价 + 名称测试（mock 共享连接，不打网）。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from vgrid.data.mootdx_quotes import MootdxQuotes


class _FakeClient:
    """模拟 mootdx client：quotes 返回预设现货表，stocks 按市场返回名录。"""

    def __init__(
        self,
        quotes_df: pd.DataFrame | None = None,
        stocks: dict[int, pd.DataFrame] | None = None,
    ) -> None:
        self._quotes_df = quotes_df
        self._stocks = stocks or {}
        self.quote_calls: list[list[str]] = []

    def quotes(self, symbol: list[str]) -> pd.DataFrame | None:
        self.quote_calls.append(list(symbol))
        return self._quotes_df

    def stocks(self, market: int) -> pd.DataFrame | None:
        return self._stocks.get(market)


def _patch(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    monkeypatch.setattr(
        "vgrid.data.mootdx_client.Quotes",
        SimpleNamespace(factory=lambda **kw: client),
    )


def _quotes_df(rows: list[tuple[str, float, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [r[0] for r in rows],
            "price": [r[1] for r in rows],
            "last_close": [r[2] for r in rows],
            "open": [r[3] for r in rows],
            "high": [r[4] for r in rows],
            "low": [r[5] for r in rows],
        }
    )


def test_snapshot_maps_and_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _quotes_df(
        [
            ("159920", 1.246, 1.229, 1.230, 1.250, 1.220),
            ("513100", 1.512, 1.519, 1.515, 1.520, 1.500),
        ]
    )
    _patch(monkeypatch, _FakeClient(quotes_df=df))
    snaps = MootdxQuotes().snapshot(["513100", "159920"])
    assert [s.code for s in snaps] == ["513100", "159920"]  # 保请求序
    assert snaps[1].price == Decimal("1.246")
    assert snaps[1].last_close == Decimal("1.229")


def test_snapshot_skips_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _quotes_df([("159920", 1.2, 1.1, 1.1, 1.3, 1.0)])
    _patch(monkeypatch, _FakeClient(quotes_df=df))
    snaps = MootdxQuotes().snapshot(["999999", "159920"])
    assert [s.code for s in snaps] == ["159920"]  # 未知代码跳过


def test_snapshot_zero_last_close_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _quotes_df([("159920", 1.2, 0.0, 1.1, 1.3, 1.0)])
    _patch(monkeypatch, _FakeClient(quotes_df=df))
    snap = MootdxQuotes().snapshot(["159920"])[0]
    assert snap.last_close is None  # 昨收 0 当作缺，别算出假涨跌


def test_snapshot_empty_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _FakeClient())
    assert MootdxQuotes().snapshot([]) == []


def test_snapshot_none_df_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _FakeClient(quotes_df=None))
    assert MootdxQuotes().snapshot(["159920"]) == []


def test_names_merges_both_markets(monkeypatch: pytest.MonkeyPatch) -> None:
    sz = pd.DataFrame({"code": ["159920"], "name": ["恒生ETF"]})
    sh = pd.DataFrame({"code": ["510300"], "name": ["沪深300ETF"]})
    _patch(monkeypatch, _FakeClient(stocks={0: sz, 1: sh}))
    names = MootdxQuotes().names()
    assert names["159920"] == "恒生ETF"
    assert names["510300"] == "沪深300ETF"
