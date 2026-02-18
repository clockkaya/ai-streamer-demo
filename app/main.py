from fastapi import FastAPI
from fastapi.responses import JSONResponse
# --- 新增：导入我们刚写的路由模块 ---
from app.api import chat
# --- 新增：导入 ws 路由 ---
from app.api import ws

app = FastAPI(
    title="AI Streamer Backend",
    description="AI 虚拟主播后端核心 API",
    version="0.1.0"
)

# --- 新增：挂载业务路由，统一加个 /api 前缀 ---
app.include_router(chat.router, prefix="/api", tags=["Live Chat"])
# --- 新增：挂载 WebSocket 路由 ---
app.include_router(ws.router, tags=["WebSocket Live"])

@app.get("/health", tags=["System"])
async def health_check():
    """验证服务是否正常运行"""
    return JSONResponse(content={"status": "ok", "message": "AI主播系统已就绪！🚀"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)