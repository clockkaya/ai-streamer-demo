"""
app.api.chat
~~~~~~~~~~~~~

HTTP REST 接口 —— 处理观众弹幕（非流式）。

提供 ``POST /api/chat`` 端点，接收弹幕文本并返回 AI 主播的完整回复。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.response import ApiResponse
from app.services.chat_service import chat_service

router: APIRouter = APIRouter()


class ChatRequest(BaseModel):
    """弹幕请求体。"""

    message: str = Field(..., description="观众发送的弹幕文本")


class ChatResponseData(BaseModel):
    """聊天响应数据。"""

    user_message: str = Field(..., description="观众原始弹幕")
    bot_reply: str = Field(..., description="AI 主播的回复")


@router.post("/chat", summary="发送直播弹幕", response_model=ApiResponse[ChatResponseData])
async def send_danmaku(request: ChatRequest) -> ApiResponse[ChatResponseData]:
    """模拟直播间观众发送弹幕，获取 AI 主播的回复。

    Args:
        request: 包含弹幕文本的请求体。

    Returns:
        统一格式的 JSON 响应，包含原始弹幕和 AI 回复。
    """
    # 调用业务服务层处理弹幕
    reply: str = await chat_service.handle_message(request.message)

    return ApiResponse.ok(
        data=ChatResponseData(
            user_message=request.message,
            bot_reply=reply,
        ),
    )