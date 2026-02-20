"""
app.api.ws
~~~~~~~~~~

WebSocket 实时交互接口 —— 多房间直播间模式。

提供 ``/ws/rooms/{room_id}`` 端点，观众通过 room_id 加入指定直播间。
同一房间内所有连接共享主播对话上下文，弹幕和回复广播给房间内所有观众。
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.live_service import get_live_service
from app.tts.engine import generate_audio_base64

logger = get_logger(__name__)

router: APIRouter = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket 直播间端点。

    通过 URL 中的 ``room_id`` 加入指定房间。同一房间内的所有观众
    共享主播对话上下文，弹幕和回复广播给房间内全体观众。

    消息协议:
      - ``[USER:消息内容]`` —— 广播观众弹幕
      - 普通文本 —— 主播流式回复
      - ``[AUDIO:base64]`` —— TTS 语音
      - ``[EOF]`` —— 本轮对话结束标记

    Args:
        websocket: FastAPI WebSocket 连接对象。
        room_id: 直播间唯一标识。
    """
    # 获取（或自动创建）目标房间
    room = get_live_service().get_room(room_id)
    await room.manager.connect(websocket)
    logger.info("观众进入直播间 | room=%s | 在线: %d", room_id, room.online_count)

    try:
        while True:
            user_message: str = await websocket.receive_text()

            # 阶段 1: 广播弹幕
            await room.manager.broadcast(f"[USER:{user_message}]")

            # 阶段 2: 流式回复，广播给房间内所有人
            full_reply: str = ""
            async for chunk in room.session.handle_message_stream(user_message):
                full_reply += chunk
                await room.manager.broadcast(chunk)
                await asyncio.sleep(0.02)

            # 阶段 3: TTS 语音合成
            if full_reply.strip():
                logger.info("TTS: 正在生成语音... | room=%s", room_id)
                audio_b64: str = await generate_audio_base64(full_reply)
                if audio_b64:
                    await room.manager.broadcast(f"[AUDIO:{audio_b64}]")
                    logger.info("TTS: 语音推送完成 | room=%s", room_id)

            # 阶段 4: 结束标记
            await room.manager.broadcast("[EOF]")

    except WebSocketDisconnect:
        room.manager.disconnect(websocket)
        logger.info("观众退出直播间 | room=%s | 在线: %d", room_id, room.online_count)
    except Exception as e:
        logger.error("WebSocket 异常: %s | room=%s", e, room_id, exc_info=True)
        room.manager.disconnect(websocket)