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
from fastapi import APIRouter, Query, Request, Depends

from app.schemas.api_response import ApiResponse
from app.schemas.live_interactions import (
    ChatMessageData,
    DanmakuRequest,
    DanmakuResponseData,
    HistoryResponseData,
    RoomInfoData,
)
from app.core.rate_limit import limiter
from app.services.live_system import LiveSystem
from app.api.deps import get_live_system

router: APIRouter = APIRouter()


# ── 房间管理端点 ──────────────────────────────────────────────────────


@router.get("/rooms", summary="获取活跃房间列表", response_model=ApiResponse[list[RoomInfoData]])
@limiter.limit("10/second")
async def list_rooms(request: Request, system: LiveSystem = Depends(get_live_system)):
    """返回所有已创建的活跃直播间列表。"""
    rooms = system.list_rooms()
    return ApiResponse.ok(data=rooms)


@router.get("/rooms/{room_id}", summary="获取房间详情", response_model=ApiResponse[RoomInfoData])
@limiter.limit("5/second")
async def room_info(request: Request, room_id: str, persona_id: str | None = None, system: LiveSystem = Depends(get_live_system)):
    """返回指定直播间的详细信息（在线人数等）。

    如果房间不存在，会自动创建。

    Args:
        room_id: 直播间唯一标识。
        persona_id: (可选)新建房间时指定的主播灵魂包 ID。
    """
    room = await system.get_room(room_id, persona_id=persona_id)
    return ApiResponse.ok(data=room.info())


# ── 弹幕端点 ──────────────────────────────────────────────────────────

@router.post(
    "/rooms/{room_id}/danmaku",
    summary="发送直播弹幕",
    response_model=ApiResponse[DanmakuResponseData],
)
@limiter.limit("1/second")
async def send_danmaku(
    request: Request,
    room_id: str, 
    danmaku_request: DanmakuRequest, 
    persona_id: str | None = None,
    system: LiveSystem = Depends(get_live_system),
):
    """向指定直播间发送弹幕，获取 AI 主播的回复。

    每次请求创建一次性 BotContext（无状态，不保留上下文）。
    注意：通过此 HTTP 接口发送的弹幕及回复不会持久化到数据库。
    如果需要保留上下文和历史记录，请使用 WebSocket 接口连接所在房间。

    Args:
        request: FastAPI Request 对象（用于限流判断）。
        room_id: 直播间唯一标识。
        danmaku_request: 包含弹幕文本的请求体。
        persona_id: (可选)使用的角色包 ID。
    """
    session = system.create_session(persona_id=persona_id)
    reply: str = await session.handle_message(danmaku_request.message)

    return ApiResponse.ok(
        data=DanmakuResponseData(
            user_message=danmaku_request.message,
            bot_reply=reply,
        ),
    )


# ── 历史回看端点 ──────────────────────────────────────────────────────

@router.get(
    "/rooms/{room_id}/history",
    summary="获取对话历史",
    response_model=ApiResponse[HistoryResponseData],
)
@limiter.limit("10/second")
async def get_history(
    request: Request,
    room_id: str,
    skip: int = Query(0, ge=0, description="跳过条数（分页偏移）"),
    limit: int = Query(100, ge=1, le=500, description="每页最大条数"),
    system: LiveSystem = Depends(get_live_system),
):
    """获取指定直播间的对话历史记录（分页，按时间正序）。

    Args:
        request: FastAPI Request 对象（用于限流判断）。
        room_id: 直播间唯一标识。
        skip: 跳过条数（分页偏移）。
        limit: 每页最大条数（1-500）。
    """
    messages = await system.repo.get_all_messages(
        room_id, skip=skip, limit=limit,
    )
    total_messages = await system.repo.count_messages(room_id)

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
            total=total_messages,
        ),
    )
