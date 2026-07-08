"""红利 ETF 池筛选测试。"""

from __future__ import annotations

from vgrid.income.universe import EtfRef, filter_dividend_etfs


def test_matches_keyword_and_etf_only() -> None:
    names = {
        "510880": "华泰柏瑞上证红利ETF",
        "512890": "华泰柏瑞中证红利低波动ETF",
        "515180": "华夏中证红利ETF",
        "600000": "浦发银行",  # 非 ETF，含"红利"也不要（其实不含）
        "159901": "深证100ETF",  # ETF 但不含关键词
        "000001": "红利主题混合",  # 含关键词但非 ETF（无 ETF 字样）
    }
    pool = filter_dividend_etfs(names)
    codes = [e.code for e in pool]
    assert codes == ["510880", "512890", "515180"]
    assert EtfRef(code="510880", name="华泰柏瑞上证红利ETF") in pool


def test_high_dividend_keyword() -> None:
    names = {"563180": "高股息ETF", "159999": "科技ETF"}
    assert [e.code for e in filter_dividend_etfs(names)] == ["563180"]


def test_custom_keywords() -> None:
    names = {"561960": "央企红利ETF", "510880": "上证红利ETF"}
    pool = filter_dividend_etfs(names, keywords=["央企红利"])
    assert [e.code for e in pool] == ["561960"]


def test_empty_names() -> None:
    assert filter_dividend_etfs({}) == []
