"""红利 ETF 池：按名称关键词从全市场证券名录里筛出候选。

纯函数——吃一份「代码→名称」的名录（由调用方从 ``MootdxQuotes.names()`` 取），
按关键词命中且是 ETF 的留下。是否真有日线走势的验证，交给上层拉行情时做（这里不打网）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# 红利相关关键词（需求 §4.1）。
DEFAULT_KEYWORDS: tuple[str, ...] = ("红利", "红利低波", "央企红利", "国企红利", "高股息")


@dataclass(frozen=True, slots=True)
class EtfRef:
    """一只候选红利 ETF 的身份。"""

    code: str
    name: str


def filter_dividend_etfs(
    names: Mapping[str, str],
    keywords: Sequence[str] = DEFAULT_KEYWORDS,
) -> list[EtfRef]:
    """从名录里筛红利 ETF：名称命中任一关键词、且名称含 "ETF"，按代码排序去重。"""
    kws = tuple(keywords)
    pool: dict[str, EtfRef] = {}
    for code, name in names.items():
        if "ETF" not in name.upper():
            continue
        if any(kw in name for kw in kws):
            pool[code] = EtfRef(code=code, name=name)
    return [pool[code] for code in sorted(pool)]
