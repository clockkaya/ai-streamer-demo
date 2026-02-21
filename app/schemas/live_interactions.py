"""
app.schemas.live_interactions
~~~~~~~~~~~~~~~~

直播间相关的 Pydantic 请求/响应模型。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MessageRole = Literal["user", "model"]


class DanmakuRequest(BaseModel):
    """弹幕请求体。"""

    message: str = Field(
        ..., min_length=1, max_length=500, description="观众发送的弹幕文本",
    )


class DanmakuResponseData(BaseModel):
    """弹幕响应数据。"""

    user_message: str = Field(..., description="观众原始弹幕")
    bot_reply: str = Field(..., description="AI 主播的回复")


class ChatMessageData(BaseModel):
    """单条对话消息。"""

    role: MessageRole = Field(..., description="消息角色：user / model")
    content: str = Field(..., description="消息文本")
    created_at: str = Field(..., description="创建时间（ISO 格式）")


class RoomInfoData(BaseModel):
    """房间摘要信息数据类型"""

    room_id: str = Field(..., description="房间唯一标识")
    persona_id: str = Field(..., description="所属主播灵魂包标识")
    online_count: int = Field(..., description="当前在线观众数")


class HistoryResponseData(BaseModel):
    """对话历史响应数据。"""

    room_id: str = Field(..., description="房间 ID")
    messages: list[ChatMessageData] = Field(..., description="消息列表")
    total: int = Field(..., description="本次返回条数")
