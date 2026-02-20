"""
tests.test_chat_service
~~~~~~~~~~~~~~~~~~~~~~~

ChatService + ChatSession 业务服务层单元测试。

由于 ``ChatService`` 使用懒初始化（``get_chat_service()``），
import 本模块不会触发任何真实 API 调用，可安全直接导入类进行测试。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.prompts.streamer import build_rag_prompt
from app.services.chat_service import ChatService, ChatSession


# ── Prompt 组装测试 ────────────────────────────────────────────────────

class TestBuildRagPrompt:
    """测试 Prompt 组装函数。"""

    def test_with_knowledge(self) -> None:
        """有背景知识时，应组装为带 RAG 标记的 Prompt。"""
        result = build_rag_prompt("你最喜欢什么武器", "粉色流星狙击枪")

        assert "观众弹幕：你最喜欢什么武器" in result
        assert "系统检索的背景知识" in result
        assert "粉色流星狙击枪" in result

    def test_without_knowledge(self) -> None:
        """无背景知识时，应直接返回用户消息。"""
        result = build_rag_prompt("你好", "")

        assert result == "你好"


# ── ChatSession 协调测试 ──────────────────────────────────────────────

class TestChatSession:
    """测试 ChatSession 的消息处理流程。"""

    @pytest.mark.asyncio
    async def test_handle_message_with_rag_hit(self) -> None:
        """RAG 命中时，LLM 收到的 prompt 应包含背景知识。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = "星瞳最害怕青椒"

        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="才不怕呢！哼！")

        session = ChatSession(rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你怕什么")

        mock_rag.search.assert_called_once_with("你怕什么")
        call_args = mock_bot.generate_reply.call_args[0][0]
        assert "青椒" in call_args
        assert "系统检索的背景知识" in call_args
        assert reply == "才不怕呢！哼！"

    @pytest.mark.asyncio
    async def test_handle_message_without_rag_hit(self) -> None:
        """RAG 未命中时，LLM 收到的 prompt 应为原始用户消息。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = ""

        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="你好呀家人们～")

        session = ChatSession(rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你好")

        call_args = mock_bot.generate_reply.call_args[0][0]
        assert call_args == "你好"
        assert reply == "你好呀家人们～"

    @pytest.mark.asyncio
    async def test_handle_message_stream(self) -> None:
        """流式处理应逐字返回完整回复。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = ""

        async def fake_stream(prompt: str) -> AsyncGenerator[str, None]:
            for char in "你好喵":
                yield char

        mock_bot = MagicMock()
        mock_bot.generate_reply_stream = fake_stream

        session = ChatSession(rag=mock_rag, bot=mock_bot)

        result_chars: list[str] = []
        async for char in session.handle_message_stream("测试"):
            result_chars.append(char)

        assert "".join(result_chars) == "你好喵"


# ── ChatService 工厂测试 ──────────────────────────────────────────────

class TestChatService:
    """测试 ChatService 的会话管理能力。"""

    def test_get_live_session_returns_same_instance(self) -> None:
        """get_live_session 应始终返回同一实例。"""
        service = ChatService.__new__(ChatService)
        service.rag = MagicMock()
        mock_bot = MagicMock()
        mock_bot.model_name = "test-model"
        service._live_session = ChatSession(rag=service.rag, bot=mock_bot)

        session_a = service.get_live_session()
        session_b = service.get_live_session()

        assert session_a is session_b

    def test_create_session_returns_independent_sessions(self) -> None:
        """create_session 每次应返回不同的 ChatSession 实例。"""
        service = ChatService.__new__(ChatService)
        service.rag = MagicMock()
        service._live_session = None

        mock_bot_a = MagicMock()
        mock_bot_b = MagicMock()

        session_a = service.create_session(bot=mock_bot_a)
        session_b = service.create_session(bot=mock_bot_b)

        assert session_a is not session_b
        assert session_a.rag is session_b.rag
        assert session_a.bot is mock_bot_a
        assert session_b.bot is mock_bot_b
