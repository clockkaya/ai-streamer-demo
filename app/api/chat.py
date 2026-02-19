"""
app.api.chat
~~~~~~~~~~~~~

HTTP REST 接口 —— 处理观众弹幕（非流式）。

提供 ``POST /api/chat`` 端点，接收弹幕文本并返回 AI 主播的完整回复。
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chat_controller import chat_controller

router: APIRouter = APIRouter()


class ChatRequest(BaseModel):
    """弹幕请求体。"""

    message: str = Field(..., description="观众发送的弹幕文本")


class ChatResponseData(BaseModel):
    """聊天响应数据。"""

    user_message: str = Field(..., description="观众原始弹幕")
    bot_reply: str = Field(..., description="AI 主播的回复")


class ChatResponse(BaseModel):
    """统一 JSON 响应。"""

    code: int = Field(default=200, description="业务状态码")
    data: ChatResponseData
    msg: str = Field(default="success", description="状态消息")

@router.post("/chat", summary="发送直播弹幕", response_model=ChatResponse)
async def send_danmaku(request: ChatRequest) -> ChatResponse:
    """模拟直播间观众发送弹幕，获取 AI 主播的回复。

    Args:
        request: 包含弹幕文本的请求体。

    Returns:
        统一格式的 JSON 响应，包含原始弹幕和 AI 回复。
    """
    reply: str = await chat_controller.handle_message(request.message)

    return ChatResponse(
        data=ChatResponseData(
            user_message=request.message,
            bot_reply=reply,
        ),
    )