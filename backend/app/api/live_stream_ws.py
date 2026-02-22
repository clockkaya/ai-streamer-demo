"""
app.api.live_stream_ws
~~~~~~~~~~

WebSocket 实时交互接口 —— 多房间直播间模式。

提供 ``/ws/rooms/{room_id}`` 端点，观众通过 room_id 加入指定直播间。
同一房间内所有连接共享主播对话上下文，弹幕和回复广播给房间内所有观众。
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger, request_id_ctx_var
from app.core.rate_limit import WebSocketRateLimiter
from app.core.settings import settings
from app.services.live_system import LiveSystem
from app.tts.edge_tts_provider import generate_audio_base64

logger = get_logger(__name__)

router: APIRouter = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def websocket_room_endpoint(
    websocket: WebSocket, 
    room_id: str, 
    persona_id: str | None = None
) -> None:
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
    ws_req_id = f"ws-{uuid.uuid4().hex[:8]}"
    token = request_id_ctx_var.set(ws_req_id)
    
    try:
        # 获取（或自动创建）目标房间
        system: LiveSystem = websocket.app.state.live_system
        room = await system.get_room(room_id, persona_id)
        await room.broadcaster.connect(websocket)
        logger.info("观众进入直播间 | room=%s | 在线: %d", room_id, room.online_count)

        # 创建当前连接专用的限流器，按照 settings 中的配置时间限制发送间隔
        ws_limiter = WebSocketRateLimiter(interval_seconds=settings.WS_RATE_LIMIT_INTERVAL)
        # 这里可以使用 websocket 的 id 作为限流标识
        client_id = id(websocket)
        # 用于隔离接收与处理的队列，确保无论处理多慢，接收端都能按到达时间正确判断限流
        queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=20)

        async def receive_loop() -> None:
            try:
                while True:
                    user_message: str = await websocket.receive_text()
                    # 限流检查：按实际到达时间
                    if not ws_limiter.is_allowed(client_id):
                        # 如果发送过快，警告观众并立刻丢弃该消息，不放入处理队列
                        await websocket.send_text("[SYSTEM:您发送弹幕的速度太快啦，请慢一点~]")
                    else:
                        try:
                            # 尝试放入队列，若满则丢弃
                            queue.put_nowait(user_message)
                        except asyncio.QueueFull:
                            await websocket.send_text("[SYSTEM:消息处理不过来啦，请稍后重试~]")
                            logger.warning("WS 队列已满，丢弃消息 | room=%s", room_id)
            except WebSocketDisconnect:
                pass # 正常断开
            except Exception as e:
                logger.error("WebSocket 接收异常: %s | room=%s", e, room_id, exc_info=True)
            finally:
                await queue.put(None) # 发送结束信号给处理协程

        async def process_loop() -> None:
            try:
                while True:
                    user_message = await queue.get()
                    if user_message is None:
                        break

                    # 阶段 1: 广播弹幕
                    await room.broadcaster.broadcast(f"[USER:{user_message}]")

                    # 阶段 2: 流式回复，广播给房间内所有人
                    full_reply: str = ""
                    async for chunk in room.bot_context.handle_message_stream(user_message):
                        full_reply += chunk
                        await room.broadcaster.broadcast(chunk)

                    # 阶段 3: TTS 语音合成
                    if full_reply.strip():
                        logger.info("TTS: 正在生成语音... | room=%s", room_id)
                        audio_b64: str = await generate_audio_base64(
                            text=full_reply,
                            voice=room.bot_context.persona.tts.voice,
                            rate=room.bot_context.persona.tts.rate,
                            pitch=room.bot_context.persona.tts.pitch,
                        )
                        if audio_b64:
                            await room.broadcaster.broadcast(f"[AUDIO:{audio_b64}]")
                            logger.info("TTS: 语音推送完成 | room=%s", room_id)

                    # 阶段 4: 结束标记
                    await room.broadcaster.broadcast("[EOF]")
            except Exception as e:
                logger.error("WebSocket 处理异常: %s | room=%s", e, room_id, exc_info=True)

        try:
            # 并发运行接收与处理
            await asyncio.gather(receive_loop(), process_loop())
        finally:
            room.broadcaster.disconnect(websocket)
            ws_limiter.remove_client(client_id)
            logger.info("观众退出直播间 | room=%s | 在线: %d", room_id, room.online_count)
            
    finally:
        request_id_ctx_var.reset(token)