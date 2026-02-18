import edge_tts
import base64

# 选择一个符合“星瞳”傲娇二次元人设的声音
# "zh-CN-XiaoyiNeural" 是微软晓伊，声音比较年轻活泼，非常适合虚拟主播
VOICE_MODEL = "zh-CN-XiaoyiNeural"


async def generate_audio_base64(text: str) -> str:
    """
    将文本转换为音频，并直接返回 Base64 字符串（不落盘存文件）
    """
    try:
        # 配置 Edge TTS
        communicate = edge_tts.Communicate(text, VOICE_MODEL)

        audio_data = bytearray()
        # 异步流式获取生成的音频字节
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        # 将音频字节转换为 Base64 字符串
        base64_audio = base64.b64encode(audio_data).decode("utf-8")
        return base64_audio
    except Exception as e:
        print(f"❌ [TTS 报错]: {str(e)}")
        return ""