"""
tests.test_live_system
~~~~~~~~~~~~~~~~~~~~~~~

LiveSystem + BotContext + LiveRoom 业务服务层单元测试。

由于 ``LiveSystem`` 使用懒初始化（``get_live_system()``），
import 本模块不会触发任何真实 API 调用。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.persona import PersonaConfig, PersonaBundle
from app.services.live_system import LiveSystem
from app.services.live_room import LiveRoom
from app.services.bot_context import BotContext


def mock_persona() -> PersonaConfig:
    return PersonaConfig(
        name="MockBot",
        description="Mock description",
        system_prompt="Mock system prompt",
        tts={"voice": "mock-voice", "rate": "+0%", "pitch": "0Hz"},
        rag={"chunk_size": 100, "chunk_overlap": 10, "search_top_k": 2},
    )

# ── BotContext 协调测试 ──────────────────────────────────────────────

class TestBotContext:
    """测试 BotContext 的消息处理流程。"""

    @pytest.mark.asyncio
    async def test_handle_message_with_rag_hit(self) -> None:
        """RAG 命中时，LLM 收到的 prompt 应包含背景知识。"""
        mock_rag = MagicMock()
        mock_rag.search = AsyncMock(return_value="星瞳最害怕青椒")

        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="才不怕呢！哼！")

        session = BotContext(persona=mock_persona(), rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你怕什么")

        mock_rag.search.assert_called_once_with("你怕什么", top_k=2)
        call_args = mock_bot.generate_reply.call_args[0][0]
        assert "青椒" in call_args
        assert "系统检索的背景知识" in call_args
        assert reply == "才不怕呢！哼！"

    @pytest.mark.asyncio
    async def test_handle_message_without_rag_hit(self) -> None:
        """RAG 未命中时，LLM 收到的 prompt 应为原始用户消息。"""
        mock_rag = MagicMock()
        mock_rag.search = AsyncMock(return_value="")

        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="你好呀家人们～")

        session = BotContext(persona=mock_persona(), rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你好")

        call_args = mock_bot.generate_reply.call_args[0][0]
        assert call_args == "你好"
        assert reply == "你好呀家人们～"

    @pytest.mark.asyncio
    async def test_handle_message_stream(self) -> None:
        """流式处理应逐字返回完整回复。"""
        mock_rag = MagicMock()
        mock_rag.search = AsyncMock(return_value="")

        async def fake_stream(prompt: str) -> AsyncGenerator[str, None]:
            for char in "你好喵":
                yield char

        mock_bot = MagicMock()
        mock_bot.generate_reply_stream = fake_stream

        session = BotContext(persona=mock_persona(), rag=mock_rag, bot=mock_bot)

        result_chars: list[str] = []
        async for char in session.handle_message_stream("测试"):
            result_chars.append(char)

        assert "".join(result_chars) == "你好喵"

    @pytest.mark.asyncio
    async def test_handle_message_persists_to_repo(self) -> None:
        """有 repo 时，handle_message 应保存 user + model 消息。"""
        mock_rag = MagicMock()
        mock_rag.search = AsyncMock(return_value="")
        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="喵~")

        mock_repo = MagicMock()
        mock_repo.save_message = AsyncMock()

        session = BotContext(
            persona=mock_persona(), rag=mock_rag, bot=mock_bot,
            repo=mock_repo, room_id="star",
        )
        await session.handle_message("测试持久化")

        assert mock_repo.save_message.call_count == 2
        mock_repo.save_message.assert_any_call("star", "user", "测试持久化")
        mock_repo.save_message.assert_any_call("star", "model", "喵~")


# ── LiveRoom 测试 ─────────────────────────────────────────────────────

class TestLiveRoom:
    """测试 LiveRoom 封装。"""

    def test_room_info(self) -> None:
        """info() 应返回房间 ID 和在线人数。"""
        mock_bot_context = MagicMock(spec=BotContext)
        room = LiveRoom(room_id="star", persona_id="bot_star", bot_context=mock_bot_context)

        info = room.info()

        assert info.room_id == "star"
        assert info.persona_id == "bot_star"
        assert info.online_count == 0

    def test_online_count_reflects_connections(self) -> None:
        """online_count 应反映连接管理器的连接数。"""
        mock_bot_context = MagicMock(spec=BotContext)
        room = LiveRoom(room_id="test", persona_id="bot_star", bot_context=mock_bot_context)

        room.broadcaster.active_connections = [MagicMock(), MagicMock()]

        assert room.online_count == 2


# ── LiveSystem 工厂测试 ──────────────────────────────────────────────

class TestLiveSystem:
    """测试 LiveSystem 的会话和房间管理能力。"""

    def setup_method(self) -> None:
        self.mock_repo = MagicMock()
        self.mock_repo.get_history = AsyncMock(return_value=[])

        self.mock_bundle = PersonaBundle(config=mock_persona(), rag_engine=MagicMock())

        self.mock_pm = MagicMock()
        self.mock_pm.default_persona_id = "bot_star"
        self.mock_pm.get_bundle.return_value = self.mock_bundle

        self.service = LiveSystem.__new__(LiveSystem)
        self.service.repo = self.mock_repo
        self.service.pm = self.mock_pm
        self.service._rooms = {}

    @pytest.mark.asyncio
    async def test_get_room_creates_room_lazily(self) -> None:
        """首次 get_room 应创建新房间，再次调用返回同一实例。"""
        room_a = await self.service.get_room("star")
        room_b = await self.service.get_room("star")

        assert room_a is room_b
        assert room_a.room_id == "star"
        assert room_a.persona_id == "bot_star"

    @pytest.mark.asyncio
    async def test_get_room_different_ids_independent(self) -> None:
        """不同 room_id 应返回不同的独立房间。"""
        room_star = await self.service.get_room("star")
        room_moon = await self.service.get_room("moon")

        assert room_star is not room_moon
        assert room_star.bot_context is not room_moon.bot_context

    @pytest.mark.asyncio
    async def test_list_rooms(self) -> None:
        """list_rooms 应返回所有已创建房间的摘要。"""
        await self.service.get_room("star")
        await self.service.get_room("moon")

        rooms = self.service.list_rooms()
        room_ids = [r.room_id for r in rooms]

        assert len(rooms) == 2
        assert "star" in room_ids
        assert "moon" in room_ids

    def test_create_session_returns_independent_sessions(self) -> None:
        """create_session 每次应返回不同的 BotContext 实例。"""
        mock_bot_a = MagicMock()
        mock_bot_b = MagicMock()

        session_a = self.service.create_session(bot=mock_bot_a)
        session_b = self.service.create_session(bot=mock_bot_b)

        assert session_a is not session_b
        assert session_a.persona is session_b.persona
        assert session_a.bot is mock_bot_a
        assert session_b.bot is mock_bot_b

    @pytest.mark.asyncio
    async def test_get_room_restores_history(self) -> None:
        """get_room 应从 repo 加载历史并传给 bot。"""
        self.service.repo.get_history = AsyncMock(return_value=[
            {"role": "user", "content": "你好"},
            {"role": "model", "content": "你好喵~"},
        ])

        room = await self.service.get_room("star")

        # 验证 repo 被调用了一次
        self.service.repo.get_history.assert_called_once()
        assert room.room_id == "star"
        # session 应关联了 repo 和 room_id
        assert room.bot_context.repo is self.service.repo
        assert room.bot_context.room_id == "star"
