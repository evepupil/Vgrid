"""网格触发信号推送：把模拟盘的成交信号推到微信（server酱 / pushplus）。

``Notifier`` 协议（类比 :class:`~vgrid.paper.realtime.RealtimeProvider`，可注入）。
切10a 只通知不真下单——模拟盘照常按 ``engine.step`` 虚拟成交记账，Notifier 把每批
成交信号推给人，人工在手机 APP 跟单。切10b 的光大 QMT Executor 就在此接口位置把
``send`` 换成"调 xtquant 真实下单"，接口不动、只换实现。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Protocol, runtime_checkable

from vgrid.core.enums import Side
from vgrid.core.models import Fill


@runtime_checkable
class Notifier(Protocol):
    """网格成交信号推送（切10a：只通知不下单）。"""

    def send(self, fills: list[Fill], *, symbol: str) -> None: ...


def format_fills(fills: list[Fill], *, symbol: str) -> str:
    """一批成交 → markdown 文本（server酱 / pushplus 共用）。"""
    lines = [f"**{symbol}** 网格触发 {len(fills)} 笔", ""]
    for f in fills:
        side = "买入" if f.side is Side.BUY else "卖出"
        ts = f.ts.strftime("%H:%M:%S") if f.ts else "--"
        line = f"- {side} **{f.shares}** 份 @ `{f.price}`（{ts}，费 {f.fee}）"
        if f.realized_pnl is not None:
            line += f"  → 已实现 {f.realized_pnl}"
        lines.append(line)
    return "\n".join(lines)


def post_form(url: str, fields: dict[str, str]) -> None:
    """``application/x-www-form-urlencoded`` POST（标准库，零依赖）。"""
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def post_json(url: str, payload: dict[str, object]) -> None:
    """``application/json`` POST。"""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()
