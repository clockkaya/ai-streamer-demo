from fastapi import APIRouter
from pydantic import BaseModel
from app.llm.gemini_bot import streamer_bot

# 相当于创建一个 Controller 或子路由组
router = APIRouter()


# 定义请求体结构 (DTO)
class ChatRequest(BaseModel):
    message: str  # 接收观众的弹幕内容


# 定义 POST 接口
@router.post("/chat", summary="发送直播弹幕")
async def send_danmaku(request: ChatRequest):
    """
    模拟直播间观众发送弹幕，获取 AI 主播的回复。
    """
    # 调用大模型生成回复 (挂起等待 IO 响应)
    reply = await streamer_bot.generate_reply(request.message)

    # 返回 JSON 格式的统一响应
    return {
        "code": 200,
        "data": {
            "user_message": request.message,
            "bot_reply": reply
        },
        "msg": "success"
    }