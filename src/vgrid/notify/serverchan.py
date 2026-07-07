"""server酱（SCT）微信推送。

sendkey 拿自环境变量 ``SERVERCHAN_SENDKEY``（https://sct.ftqq.com/ 的 SendKey）。
HTTP 一个 POST 到 ``{sendkey}.send``，``title`` + ``desp``（markdown 正文）。
"""

from __future__ import annotations

from vgrid.core.models import Fill
from vgrid.notify.base import format_fills, post_form


class ServerChanNotifier:
    """server酱推送。"""

    _URL = "https://sct.ftqq.com/{key}.send"

    def __init__(self, sendkey: str) -> None:
        self._sendkey = sendkey

    def send(self, fills: list[Fill], *, symbol: str) -> None:
        if not fills:
            return
        post_form(
            self._URL.format(key=self._sendkey),
            {
                "title": f"网格 {symbol} {len(fills)} 笔",
                "desp": format_fills(fills, symbol=symbol),
            },
        )
