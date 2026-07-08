"""notify —— 网格触发信号推送（切10a：半自动实盘，只通知不下单）。

``Notifier`` 是执行 / 通知抽象的雏形——切10b 的光大 QMT Executor 在此接口位置换成
"调 xtquant 真实下单"。通道：server酱 / pushplus（皆推微信，HTTP POST）。token 走
环境变量，不进代码 / 不进 git。
"""

from __future__ import annotations

import os

from vgrid.notify.base import Notifier
from vgrid.notify.pushplus import PushPlusNotifier
from vgrid.notify.serverchan import ServerChanNotifier

__all__ = [
    "Notifier",
    "PushPlusNotifier",
    "ServerChanNotifier",
    "make_notifier",
]


def make_notifier(channel: str) -> Notifier:
    """按通道名 + 环境变量建 Notifier。

    缺凭证抛 ``ValueError``（人话报错）。调用方（CLI）应捕获退 1，不让 traceback 冒出。
    """
    if channel == "serverchan":
        key = os.environ.get("SERVERCHAN_SENDKEY")
        if not key:
            raise ValueError("推送缺凭证：设环境变量 SERVERCHAN_SENDKEY（sct.ftqq.com 的 SendKey）")
        return ServerChanNotifier(key)
    if channel == "pushplus":
        token = os.environ.get("PUSHPLUS_TOKEN")
        if not token:
            raise ValueError("推送缺凭证：设环境变量 PUSHPLUS_TOKEN（pushplus.plus 的 token）")
        return PushPlusNotifier(token)
    raise ValueError(f"未知推送通道：{channel}（可选：serverchan / pushplus）")
