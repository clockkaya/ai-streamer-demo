"""
app.api.ws
~~~~~~~~~~

WebSocket 实时交互接口 —— 流式弹幕 + TTS 语音推送。

提供 ``/ws/chat`` 端点，支持打字机式流式输出和音频实时推送。
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.chat_service import chat_service
from app.tts.engine import generate_audio_base64

logger = get_logger(__name__)

router: APIRouter = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket 直播间聊天端点。

    连接后持续监听用户消息，每次收到弹幕后：

    1. 通过 ChatService 流式获取 AI 回复并逐字推送
    2. 整句回复完成后，调用 TTS 引擎生成语音
    3. 以 ``[AUDIO:base64]`` 格式推送音频
    4. 发送 ``[EOF]`` 结束标记

    Args:
        websocket: FastAPI WebSocket 连接对象。
    """
    await websocket.accept()
    try:
        while True:
            user_message: str = await websocket.receive_text()

            # 阶段 1: 流式回复 —— 逐字推送给前端，模拟打字机效果
            full_reply: str = ""
            async for chunk in chat_service.handle_message_stream(user_message):
                full_reply += chunk
                await websocket.send_text(chunk)
                await asyncio.sleep(0.02)  # 控制打字速度

            # 阶段 2: TTS 语音合成 —— 将整句回复转为音频推送
            if full_reply.strip():
                logger.info("TTS: 正在生成语音...")
                audio_b64: str = await generate_audio_base64(full_reply)
                if audio_b64:
                    await websocket.send_text(f"[AUDIO:{audio_b64}]")
                    logger.info("TTS: 语音推送完成")

            # 阶段 3: 结束标记 —— 通知前端本轮对话结束
            await websocket.send_text("[EOF]")

    except WebSocketDisconnect:
        logger.info("观众退出了直播间")
    except Exception as e:
        logger.error("WebSocket 异常: %s", e, exc_info=True)
        await websocket.send_text(f"服务器开小差了: {e!s}")