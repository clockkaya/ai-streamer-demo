"""
tests.test_tts_engine
~~~~~~~~~~~~~~~~~~~~~

TTS 语音合成引擎单元测试。

所有 Edge-TTS 网络调用通过 mock 替代，不依赖网络。
"""
from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_generate_audio_returns_base64() -> None:
    """正常输入应返回合法的 Base64 字符串。"""
    fake_audio_bytes = b"\x00\x01\x02\x03\x04\x05"

    async def fake_stream():
        yield {"type": "audio", "data": fake_audio_bytes}

    mock_communicate = MagicMock()
    mock_communicate.stream = fake_stream

    with patch("app.tts.edge_tts_provider.edge_tts.Communicate", return_value=mock_communicate):
        from app.tts.edge_tts_provider import generate_audio_base64

        result: str = await generate_audio_base64("测试文本")

    assert isinstance(result, str)
    assert len(result) > 0
    # 验证是合法 Base64
    decoded = base64.b64decode(result)
    assert decoded == fake_audio_bytes


@pytest.mark.asyncio
async def test_generate_audio_multiple_chunks() -> None:
    """多个音频 chunk 应拼接为完整 Base64。"""
    chunk1 = b"\x00\x01"
    chunk2 = b"\x02\x03"

    async def fake_stream():
        yield {"type": "audio", "data": chunk1}
        yield {"type": "metadata", "data": b"ignored"}
        yield {"type": "audio", "data": chunk2}

    mock_communicate = MagicMock()
    mock_communicate.stream = fake_stream

    with patch("app.tts.edge_tts_provider.edge_tts.Communicate", return_value=mock_communicate):
        from app.tts.edge_tts_provider import generate_audio_base64

        result: str = await generate_audio_base64("多段音频")

    decoded = base64.b64decode(result)
    assert decoded == chunk1 + chunk2


@pytest.mark.asyncio
async def test_generate_audio_exception_returns_empty() -> None:
    """TTS 引擎异常时应返回空字符串而不是抛出异常。"""
    with patch(
        "app.tts.edge_tts_provider.edge_tts.Communicate",
        side_effect=RuntimeError("网络错误"),
    ):
        from app.tts.edge_tts_provider import generate_audio_base64

        result: str = await generate_audio_base64("异常测试")

    assert result == ""
