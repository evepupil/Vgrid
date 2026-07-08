"""费用（管理费 / 托管费 / 销售服务费）。

第一版没有可用的 ETF 费率结构化源——实测东财 ``fund_fee_em`` 对 ETF 返回空表，
故默认返回 ``ExpenseInfo.unknown()``：报告照常展示 "unknown"，真实价格 / 净值口径下
不额外扣费（净值本就含费，避免重复扣）。留 ``fetch`` 注入点，将来接到费率源即可替换。
"""

from __future__ import annotations

from collections.abc import Callable

from vgrid.income.models import ExpenseInfo

ExpenseFetch = Callable[[str], ExpenseInfo]


def _unknown_expenses(symbol: str) -> ExpenseInfo:
    """默认：费用未知（无可用 ETF 费率源）。``symbol`` 暂不用，留作将来接费率源。"""
    _ = symbol
    return ExpenseInfo.unknown()


def fetch_expenses(symbol: str, *, fetch: ExpenseFetch = _unknown_expenses) -> ExpenseInfo:
    """取单只 ETF 的费用信息（第一版默认 unknown，可注入将来的费率源）。"""
    return fetch(symbol)
