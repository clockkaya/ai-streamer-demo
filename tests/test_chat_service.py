"""
tests.test_chat_service
~~~~~~~~~~~~~~~~~~~~~~~

ChatService + ChatSession 业务服务层单元测试。

验证：
- ChatService 创建独立 session 的能力
- ChatSession 的 RAG 检索 + Prompt 组装 + LLM 调用协调流程
- build_rag_prompt 的 Prompt 组装正确性

所有外部依赖（Gemini、FAISS Embedding）通过 mock 替代。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.prompts.streamer import build_rag_prompt


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

        # 直接构造 ChatSession，注入 mock 依赖
        from app.services.chat_service import ChatSession

        session = ChatSession(rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你怕什么")

        # 验证 RAG 被调用
        mock_rag.search.assert_called_once_with("你怕什么")
        # 验证 LLM 收到的 prompt 包含 RAG 知识
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

        from app.services.chat_service import ChatSession

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

        from app.services.chat_service import ChatSession

        session = ChatSession(rag=mock_rag, bot=mock_bot)

        result_chars: list[str] = []
        async for char in session.handle_message_stream("测试"):
            result_chars.append(char)

        assert "".join(result_chars) == "你好喵"


# ── ChatService 工厂测试 ──────────────────────────────────────────────

class TestChatService:
    """测试 ChatService 的会话创建能力。"""

    def test_create_session_returns_independent_sessions(self) -> None:
        """每次 create_session 应返回不同的 ChatSession 实例。"""
        mock_rag = MagicMock()
        mock_rag.load_corpus = MagicMock()

        mock_bot_a = MagicMock()
        mock_bot_b = MagicMock()

        from app.services.chat_service import ChatService

        service = ChatService.__new__(ChatService)
        service.rag = mock_rag

        session_a = service.create_session(bot=mock_bot_a)
        session_b = service.create_session(bot=mock_bot_b)

        # 两个 session 是不同的实例
        assert session_a is not session_b
        # 但共享同一个 RAG
        assert session_a.rag is session_b.rag
        # Bot 各自独立
        assert session_a.bot is mock_bot_a
        assert session_b.bot is mock_bot_b
