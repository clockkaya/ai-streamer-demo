"""
app.main
~~~~~~~~

FastAPI 应用入口 —— 注册路由、挂载中间件、定义生命周期。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import room, ws
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db import close_mongo, connect_mongo
from app.schemas.response import ApiResponse

# 初始化日志系统（必须在其他模块之前）
setup_logging()
logger = get_logger(__name__)


# ── 生命周期 ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期钩子，仅在 worker 启动/关闭时各执行一次。"""
    # ── 启动 ──
    await connect_mongo()
    logger.info(
        "🚀 应用已启动 | env=%s | debug=%s | log_level=%s",
        settings.ENVIRONMENT,
        settings.debug,
        settings.effective_log_level,
    )
    yield
    # ── 关闭 ──
    await close_mongo()
    logger.info("👋 应用已关闭")


# ── 创建 FastAPI 实例 ─────────────────────────────────────────────────

app: FastAPI = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI 虚拟主播后端核心 API",
    version=settings.VERSION,
    debug=settings.debug,
    lifespan=lifespan,
)

# ── CORS 中间件（中间件注册必须在模块顶层，但不需要打日志）──────────
if settings.allow_cors_all_origins:
    # dev / test 环境：允许所有来源，方便本地调试
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # prod 环境：仅允许指定来源（可在 config.py 中扩展 ALLOWED_ORIGINS 字段）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

# ── 路由挂载 ──────────────────────────────────────────────────────────
app.include_router(room.router, prefix="/api", tags=["Room & Danmaku"])
app.include_router(ws.router, tags=["WebSocket Live"])


# ── 全局异常处理器 ────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理异常，返回统一的 ApiResponse.fail() 格式。

    避免 FastAPI 默认返回 HTML 错误页面，保持 JSON 响应一致性。
    """
    logger.error("未捕获异常: %s %s -> %s", request.method, request.url, exc, exc_info=True)
    # 非 prod 环境返回详细错误信息，prod 环境隐藏内部细节
    detail = str(exc) if not settings.is_prod else "服务器内部错误"
    response = ApiResponse.fail(msg=detail, code=500, data=None)
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )


@app.get("/health", tags=["System"])
async def health_check() -> JSONResponse:
    """验证服务是否正常运行。

    Returns:
        包含服务状态信息的 JSON 响应。
    """
    return JSONResponse(
        content={
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "debug": settings.debug,
            "log_level": settings.effective_log_level,
            "message": "AI主播系统已就绪！🚀",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.reload,  # 仅 dev 环境开启热重载
        log_level=settings.effective_log_level.lower(),
    )