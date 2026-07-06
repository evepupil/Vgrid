"""FastAPI 控制台后端：组装各域 APIRouter + 旧 HTML 面板。

各域路由在 ``routes/`` 下分文件，server 只负责挂载 + 配置全局状态（默认库路径、
策略库目录）。新功能加 router 即可，不在本文件堆业务。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from vgrid.web.routes import state as state_router
from vgrid.web.routes import strategies as strategies_router

_TEMPLATE = Path(__file__).parent / "templates" / "index.html"
_DEFAULT_STRATEGIES_DIR = Path("strategies")


def create_app(
    default_db: str = ":memory:",
    *,
    strategies_dir: Path | None = None,
) -> FastAPI:
    """创建控制台 FastAPI 应用。

    Args:
        default_db: ``/api/state`` 的默认模拟盘库路径。
        strategies_dir: 策略库目录（默认 cwd 下 ``strategies/``）。
    """
    app = FastAPI(title="vgrid console")
    app.state.default_db = default_db
    app.state.strategies_dir = strategies_dir or _DEFAULT_STRATEGIES_DIR
    app.include_router(state_router.router)
    app.include_router(strategies_router.router)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _TEMPLATE.read_text(encoding="utf-8")

    return app
