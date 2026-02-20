"""
app.api.room
~~~~~~~~~~~~~

直播间 REST 接口 —— 房间管理 + 弹幕发送 + 历史回看。

路由前缀 ``/api/rooms``，所有房间相关操作统一在此处。

端点:
  - ``GET  /rooms``                       → 获取活跃房间列表
  - ``GET  /rooms/{room_id}``             → 获取房间详情
  - ``POST /rooms/{room_id}/danmaku``     → 发送弹幕（HTTP 一次性，无状态）
  - ``GET  /rooms/{room_id}/history``     → 获取对话历史（分页）
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.schemas.response import ApiResponse
from app.services.live_service import get_live_service

router: APIRouter = APIRouter()


# ── 请求/响应模型 ─────────────────────────────────────────────────────

class DanmakuRequest(BaseModel):
    """弹幕请求体。"""

    message: str = Field(..., description="观众发送的弹幕文本")


class DanmakuResponseData(BaseModel):
    """弹幕响应数据。"""

    user_message: str = Field(..., description="观众原始弹幕")
    bot_reply: str = Field(..., description="AI 主播的回复")


class ChatMessageData(BaseModel):
    """单条对话消息。"""

    role: str = Field(..., description="消息角色：user / model")
    content: str = Field(..., description="消息文本")
    created_at: str = Field(..., description="创建时间（ISO 格式）")


class HistoryResponseData(BaseModel):
    """对话历史响应数据。"""

    room_id: str = Field(..., description="房间 ID")
    messages: list[ChatMessageData] = Field(..., description="消息列表")
    total: int = Field(..., description="本次返回条数")


# ── 房间管理端点 ──────────────────────────────────────────────────────

@router.get("/rooms", summary="获取活跃房间列表")
async def list_rooms() -> ApiResponse[list[dict]]:
    """返回所有已创建的活跃直播间列表。"""
    rooms = get_live_service().list_rooms()
    return ApiResponse.ok(data=rooms)


@router.get("/rooms/{room_id}", summary="获取房间详情")
async def room_info(room_id: str) -> ApiResponse[dict]:
    """返回指定直播间的详细信息（在线人数等）。

    如果房间不存在，会自动创建。

    Args:
        room_id: 直播间唯一标识。
    """
    room = await get_live_service().get_room(room_id)
    return ApiResponse.ok(data=room.info())


# ── 弹幕端点 ──────────────────────────────────────────────────────────

@router.post(
    "/rooms/{room_id}/danmaku",
    summary="发送直播弹幕",
    response_model=ApiResponse[DanmakuResponseData],
)
async def send_danmaku(
    room_id: str, request: DanmakuRequest,
) -> ApiResponse[DanmakuResponseData]:
    """向指定直播间发送弹幕，获取 AI 主播的回复。

    每次请求创建一次性 ChatSession（无状态，不保留上下文）。

    Args:
        room_id: 直播间唯一标识。
        request: 包含弹幕文本的请求体。
    """
    session = get_live_service().create_session()
    reply: str = await session.handle_message(request.message)

    return ApiResponse.ok(
        data=DanmakuResponseData(
            user_message=request.message,
            bot_reply=reply,
        ),
    )


# ── 历史回看端点 ──────────────────────────────────────────────────────

@router.get(
    "/rooms/{room_id}/history",
    summary="获取对话历史",
    response_model=ApiResponse[HistoryResponseData],
)
async def get_history(
    room_id: str,
    skip: int = Query(0, ge=0, description="跳过条数（分页偏移）"),
    limit: int = Query(100, ge=1, le=500, description="每页最大条数"),
) -> ApiResponse[HistoryResponseData]:
    """获取指定直播间的对话历史记录（分页，按时间正序）。

    Args:
        room_id: 直播间唯一标识。
        skip: 跳过条数（分页偏移）。
        limit: 每页最大条数（1-500）。
    """
    service = get_live_service()
    messages = await service.repo.get_all_messages(
        room_id, skip=skip, limit=limit,
    )

    # 将 datetime 转为 ISO 字符串
    chat_messages = [
        ChatMessageData(
            role=msg["role"],
            content=msg["content"],
            created_at=msg["created_at"].isoformat(),
        )
        for msg in messages
    ]

    return ApiResponse.ok(
        data=HistoryResponseData(
            room_id=room_id,
            messages=chat_messages,
            total=len(chat_messages),
        ),
    )
