from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.llm.gemini_bot import streamer_bot
import asyncio
# ⚠️ 新增：导入刚才写的 TTS 引擎
from app.tts.engine import generate_audio_base64

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            user_message = await websocket.receive_text()

            # ⚠️ 新增：用来收集大模型说出的完整句子
            full_reply = ""

            async for chunk in streamer_bot.generate_reply_stream(user_message):
                # 记录完整的句子
                full_reply += chunk

                await websocket.send_text(chunk)
                await asyncio.sleep(0.02)

                # ⚠️ 新增 TTS 链路：整句话流式推送完毕后，立刻生成语音！
            if full_reply.strip():
                print("🎙️ [TTS]: 正在生成语音...")
                audio_b64 = await generate_audio_base64(full_reply)
                if audio_b64:
                    # 使用特殊标记 [AUDIO:xxx] 把声音发给前端
                    await websocket.send_text(f"[AUDIO:{audio_b64}]")
                    print("✅ [TTS]: 语音推送完成")

            # 最后发送结束标记
            await websocket.send_text("[EOF]")

    except WebSocketDisconnect:
        print("💡 [系统提示]: 观众退出了直播间")
    except Exception as e:
        await websocket.send_text(f"服务器开小差了: {str(e)}")