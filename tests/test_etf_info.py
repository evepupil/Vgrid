"""etf_info 缓存测试（注入 fake MootdxQuotes，不打网）。"""

from __future__ import annotations

from vgrid.web.etf_info import EtfInfoCache


class _FakeQuotes:
    """按预设 代码→名称 返回，记录拉取次数。"""

    def __init__(self, names: dict[str, str]) -> None:
        self._names = names
        self.calls = 0

    def names(self) -> dict[str, str]:
        self.calls += 1
        return dict(self._names)


def test_get_name() -> None:
    fake = _FakeQuotes({"159920": "恒生ETF", "510300": "沪深300ETF"})
    cache = EtfInfoCache(quotes=fake)
    assert cache.get_name("159920") == "恒生ETF"
    assert cache.get_name("510300") == "沪深300ETF"
    assert cache.get_name("000000") is None


def test_cache_reuses() -> None:
    fake = _FakeQuotes({"159920": "恒生ETF"})
    cache = EtfInfoCache(quotes=fake)
    cache.get_name("159920")
    cache.get_name("159920")
    assert fake.calls == 1  # 第二次走缓存


def test_empty_pull_does_not_cache() -> None:
    """拉空（连接失败）不刷缓存，下次重试。"""
    fake = _FakeQuotes({})
    cache = EtfInfoCache(quotes=fake)
    assert cache.get_name("159920") is None
    assert cache.get_name("159920") is None
    assert fake.calls == 2  # 空结果没缓存，每次都重拉
