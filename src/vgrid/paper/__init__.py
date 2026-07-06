"""paper —— 模拟盘（实时轮询 + 虚拟账户 + replay）。复用 M1 引擎，一行不改。"""

from vgrid.paper.realtime import AkshareRealtimeProvider, RealtimeProvider
from vgrid.paper.runner import PaperRunner, PaperSnapshot
from vgrid.paper.session import in_session, next_session_open

__all__ = [
    "AkshareRealtimeProvider",
    "PaperRunner",
    "PaperSnapshot",
    "RealtimeProvider",
    "in_session",
    "next_session_open",
]
