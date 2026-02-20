"""
app.api.ws
~~~~~~~~~~

WebSocket 实时交互接口 —— 直播间模式。

所有连接共享同一主播对话上下文，通过 ``ConnectionManager`` 广播弹幕和回复。
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.chat_service import get_chat_service
from app.tts.engine import generate_audio_base64

logger = get_logger(__name__)

router: APIRouter = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器 —— 维护在线观众列表，提供广播能力。"""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """接受新连接并加入在线列表。"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("观众进入直播间 | 当前在线: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """从在线列表移除断开的连接。"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("观众退出直播间 | 当前在线: %d", len(self.active_connections))

    async def broadcast(self, message: str) -> None:
        """向所有在线观众广播消息。"""
        tasks = [ws.send_text(message) for ws in self.active_connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 清理已断开的连接
        for ws, result in zip(self.active_connections[:], results):
            if isinstance(result, Exception):
                logger.warning("广播失败，移除断开的连接")
                self.active_connections.remove(ws)


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket 直播间聊天端点。

    所有连接共享同一主播对话上下文。弹幕和回复广播给所有在线观众。

    消息协议:
      - ``[USER:消息内容]`` —— 广播观众弹幕
      - 普通文本 —— 主播流式回复
      - ``[AUDIO:base64]`` —— TTS 语音
      - ``[EOF]`` —— 本轮对话结束标记
    """
    await manager.connect(websocket)

    # 所有连接共享同一个直播间会话
    session = get_chat_service().get_live_session()

    try:
        while True:
            user_message: str = await websocket.receive_text()

            # 阶段 1: 广播弹幕
            await manager.broadcast(f"[USER:{user_message}]")

            # 阶段 2: 流式回复，广播给所有人
            full_reply: str = ""
            async for chunk in session.handle_message_stream(user_message):
                full_reply += chunk
                await manager.broadcast(chunk)
                await asyncio.sleep(0.02)

            # 阶段 3: TTS 语音合成
            if full_reply.strip():
                logger.info("TTS: 正在生成语音...")
                audio_b64: str = await generate_audio_base64(full_reply)
                if audio_b64:
                    await manager.broadcast(f"[AUDIO:{audio_b64}]")
                    logger.info("TTS: 语音推送完成")

            # 阶段 4: 结束标记
            await manager.broadcast("[EOF]")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket 异常: %s", e, exc_info=True)
        manager.disconnect(websocket)