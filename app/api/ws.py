"""
app.api.ws
~~~~~~~~~~

WebSocket 实时交互接口 —— 流式弹幕 + TTS 语音推送。

提供 ``/ws/chat`` 端点，支持打字机式流式输出和音频实时推送。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.chat_controller import chat_controller
from app.tts.engine import generate_audio_base64

router: APIRouter = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """WebSocket 直播间聊天端点。

    连接后持续监听用户消息，每次收到弹幕后：

    1. 通过 ChatController 流式获取 AI 回复并逐字推送
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

            full_reply: str = ""
            async for chunk in chat_controller.handle_message_stream(user_message):
                full_reply += chunk
                await websocket.send_text(chunk)
                await asyncio.sleep(0.02)

            # TTS 语音合成与推送
            if full_reply.strip():
                print("🎙️ [TTS]: 正在生成语音...")
                audio_b64: str = await generate_audio_base64(full_reply)
                if audio_b64:
                    await websocket.send_text(f"[AUDIO:{audio_b64}]")
                    print("✅ [TTS]: 语音推送完成")

            # 结束标记
            await websocket.send_text("[EOF]")

    except WebSocketDisconnect:
        print("💡 [系统提示]: 观众退出了直播间")
    except Exception as e:
        await websocket.send_text(f"服务器开小差了: {e!s}")