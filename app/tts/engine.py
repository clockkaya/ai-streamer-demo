"""
app.tts.engine
~~~~~~~~~~~~~~

基于 Edge-TTS 的语音合成引擎。

将文本异步转换为 Base64 编码的 MP3 音频，直接内存传输不落盘。
TTS 语音模型从配置中心 ``settings.TTS_VOICE`` 读取。
"""

from __future__ import annotations

import base64

import edge_tts

from app.core.config import settings


async def generate_audio_base64(text: str) -> str:
    """将文本转换为音频并返回 Base64 编码字符串。

    使用 Edge-TTS 异步流式获取音频字节，完成后编码为 Base64。
    不会在磁盘上生成临时文件。

    Args:
        text: 待合成的文本内容。

    Returns:
        MP3 音频的 Base64 字符串。合成失败时返回空字符串。
    """
    try:
        communicate = edge_tts.Communicate(text, settings.TTS_VOICE)

        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        base64_audio: str = base64.b64encode(audio_data).decode("utf-8")
        return base64_audio
    except Exception as e:
        print(f"❌ [TTS 报错]: {e!s}")
        return ""