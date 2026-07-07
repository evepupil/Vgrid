"""PushPlus 微信推送。

token 拿自环境变量 ``PUSHPLUS_TOKEN``（https://www.pushplus.plus/ 的 token）。
POST JSON ``{token, title, content}`` 到 ``/send``，``content`` 为 markdown 正文。
"""

from __future__ import annotations

from vgrid.core.models import Fill
from vgrid.notify.base import format_fills, post_json


class PushPlusNotifier:
    """PushPlus 推送。"""

    _URL = "https://www.pushplus.plus/send"

    def __init__(self, token: str) -> None:
        self._token = token

    def send(self, fills: list[Fill], *, symbol: str) -> None:
        if not fills:
            return
        post_json(
            self._URL,
            {
                "token": self._token,
                "title": f"网格 {symbol} {len(fills)} 笔",
                "content": format_fills(fills, symbol=symbol),
            },
        )
