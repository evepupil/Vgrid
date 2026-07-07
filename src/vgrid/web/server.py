"""FastAPI 控制台后端：组装各域 APIRouter + 前端静态文件。

各域路由在 ``routes/`` 下分文件，server 只负责挂载 + 配置全局状态（默认库路径、
策略库目录、数据目录）。``frontend_dist`` 指向前端构建产物（``frontend/dist``），
存在则后端直接 serve SPA（文件存在返文件，否则回退 ``index.html`` 让 react-router
接管），不存在则回退旧 HTML 面板。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from vgrid.data.provider import BarProvider
from vgrid.web.quotes import AkshareSpotProvider, QuoteProvider
from vgrid.web.routes import backtest as backtest_router
from vgrid.web.routes import etf as etf_router
from vgrid.web.routes import ladder as ladder_router
from vgrid.web.routes import portfolio as portfolio_router
from vgrid.web.routes import quotes as quotes_router
from vgrid.web.routes import scan as scan_router
from vgrid.web.routes import state as state_router
from vgrid.web.routes import strategies as strategies_router

_TEMPLATE = Path(__file__).parent / "templates" / "index.html"
_DEFAULT_STRATEGIES_DIR = Path("strategies")
_DEFAULT_DATA_DIR = Path.home() / ".vgrid"


def create_app(
    default_db: str = ":memory:",
    *,
    strategies_dir: Path | None = None,
    data_dir: Path | None = None,
    frontend_dist: Path | None = None,
    quote_provider: QuoteProvider | None = None,
    bar_provider: BarProvider | None = None,
    cache_dir: Path | None = None,
) -> FastAPI:
    """创建控制台 FastAPI 应用。

    Args:
        default_db: ``/api/state`` 的默认模拟盘库路径。
        strategies_dir: 策略库目录（默认 cwd 下 ``strategies/``）。
        data_dir: 用户数据目录（存 portfolio.sqlite + paper/ 实例 DB，默认 ``~/.vgrid``）。
        frontend_dist: 前端构建产物目录。传 ``frontend/dist`` 则后端 serve SPA
            （文件存在返文件、否则回退 index.html）；不传则回退旧 HTML 面板。
        quote_provider: 实时报价源，默认 ``AkshareSpotProvider``。测试 / 离线可注入 stub。
        bar_provider: 历史日线源（关注列表网格适配评分用），默认 ``None`` 走
            ``load_bars`` 的 akshare 默认源。测试 / 离线可注入 stub。
        cache_dir: 历史行情缓存目录，默认 ``None`` 走 ``~/.vgrid/cache``。测试可指临时目录。
    """
    app = FastAPI(title="vgrid console")
    app.state.default_db = default_db
    app.state.strategies_dir = strategies_dir or _DEFAULT_STRATEGIES_DIR
    app.state.data_dir = data_dir or _DEFAULT_DATA_DIR
    app.state.quote_provider = quote_provider or AkshareSpotProvider()
    app.state.bar_provider = bar_provider
    app.state.cache_dir = cache_dir
    app.include_router(state_router.router)
    app.include_router(strategies_router.router)
    app.include_router(backtest_router.router)
    app.include_router(portfolio_router.router)
    app.include_router(etf_router.router)
    app.include_router(ladder_router.router)
    app.include_router(quotes_router.router)
    app.include_router(scan_router.router)

    if frontend_dist is not None and frontend_dist.exists():
        dist_resolved = frontend_dist.resolve()
        index_html = dist_resolved / "index.html"

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        def spa(full_path: str) -> FileResponse:
            # 文件存在（assets / favicon 等）直接返；否则回退 index.html（react-router 接管）。
            candidate = (dist_resolved / full_path).resolve()
            if candidate.is_relative_to(dist_resolved) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_html)
    else:
        # 未 build：回退旧 HTML 面板（开发时前端走 Vite dev server 5173）。
        @app.get("/", response_class=HTMLResponse)
        def index() -> str:
            return _TEMPLATE.read_text(encoding="utf-8")

    return app
