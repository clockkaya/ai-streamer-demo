"""
app.api.live_endpoints
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

from app.schemas.api_response import ApiResponse
from app.schemas.live_interactions import (
    ChatMessageData,
    DanmakuRequest,
    DanmakuResponseData,
    HistoryResponseData,
    RoomInfoData,
)
from app.services.live_system import get_live_system

router: APIRouter = APIRouter()


# ── 房间管理端点 ──────────────────────────────────────────────────────


@router.get("/rooms", summary="获取活跃房间列表")
async def list_rooms() -> ApiResponse[list[RoomInfoData]]:
    """返回所有已创建的活跃直播间列表。"""
    rooms = get_live_system().list_rooms()
    return ApiResponse.ok(data=rooms)


@router.get("/rooms/{room_id}", summary="获取房间详情")
async def room_info(room_id: str, persona_id: str | None = None) -> ApiResponse[RoomInfoData]:
    """返回指定直播间的详细信息（在线人数等）。

    如果房间不存在，会自动创建。

    Args:
        room_id: 直播间唯一标识。
        persona_id: (可选)新建房间时指定的主播灵魂包 ID。
    """
    room = await get_live_system().get_room(room_id, persona_id=persona_id)
    return ApiResponse.ok(data=room.info())


# ── 弹幕端点 ──────────────────────────────────────────────────────────

@router.post(
    "/rooms/{room_id}/danmaku",
    summary="发送直播弹幕",
    response_model=ApiResponse[DanmakuResponseData],
)
async def send_danmaku(
    room_id: str, request: DanmakuRequest, persona_id: str | None = None,
) -> ApiResponse[DanmakuResponseData]:
    """向指定直播间发送弹幕，获取 AI 主播的回复。

    每次请求创建一次性 BotContext（无状态，不保留上下文）。
    注意：通过此 HTTP 接口发送的弹幕及回复不会持久化到数据库。
    如果需要保留上下文和历史记录，请使用 WebSocket 接口连接所在房间。

    Args:
        room_id: 直播间唯一标识。
        request: 包含弹幕文本的请求体。
        persona_id: (可选)使用的角色包 ID。
    """
    session = get_live_system().create_session(persona_id=persona_id)
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
    service = get_live_system()
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
