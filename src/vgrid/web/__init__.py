"""web —— FastAPI 看盘面板（读 SQLite，展示持仓 / 盈亏 / 成交 / 净值曲线）。"""

from vgrid.web.server import create_app
from vgrid.web.state import StateView, load_state

__all__ = ["StateView", "create_app", "load_state"]
