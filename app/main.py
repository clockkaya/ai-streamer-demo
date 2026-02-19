"""
app.main
~~~~~~~~

FastAPI 应用入口 —— 注册路由、挂载中间件、定义生命周期。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import chat, ws
from app.core.config import settings

app: FastAPI = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI 虚拟主播后端核心 API",
    version=settings.VERSION,
    debug=settings.debug,
)

# ── 路由挂载 ──────────────────────────────────────────────────────────
app.include_router(chat.router, prefix="/api", tags=["Live Chat"])
app.include_router(ws.router, tags=["WebSocket Live"])


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
            "message": "AI主播系统已就绪！🚀",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.debug,
    )