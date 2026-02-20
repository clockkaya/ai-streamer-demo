"""
tests.test_live_service
~~~~~~~~~~~~~~~~~~~~~~~

LiveService + ChatSession + LiveRoom 业务服务层单元测试。

由于 ``LiveService`` 使用懒初始化（``get_live_service()``），
import 本模块不会触发任何真实 API 调用。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.prompts.streamer import build_rag_prompt
from app.services.live_service import LiveService
from app.services.room import LiveRoom
from app.services.session import ChatSession


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

    @pytest.mark.asyncio
    async def test_handle_message_persists_to_repo(self) -> None:
        """有 repo 时，handle_message 应保存 user + model 消息。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = ""
        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="喵~")

        mock_repo = MagicMock()
        mock_repo.save_message = AsyncMock()

        session = ChatSession(
            rag=mock_rag, bot=mock_bot,
            repo=mock_repo, room_id="star",
        )
        await session.handle_message("测试持久化")

        assert mock_repo.save_message.call_count == 2
        mock_repo.save_message.assert_any_call("star", "user", "测试持久化")
        mock_repo.save_message.assert_any_call("star", "model", "喵~")

    @pytest.mark.asyncio
    async def test_handle_message_without_repo_no_persist(self) -> None:
        """无 repo 时，不应尝试持久化。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = ""
        mock_bot = MagicMock()
        mock_bot.generate_reply = AsyncMock(return_value="喵~")

        session = ChatSession(rag=mock_rag, bot=mock_bot)
        reply = await session.handle_message("你好")

        assert reply == "喵~"

    @pytest.mark.asyncio
    async def test_handle_message_stream_persists(self) -> None:
        """流式处理完成后也应持久化。"""
        mock_rag = MagicMock()
        mock_rag.search.return_value = ""

        async def fake_stream(prompt: str) -> AsyncGenerator[str, None]:
            for char in "你好":
                yield char

        mock_bot = MagicMock()
        mock_bot.generate_reply_stream = fake_stream

        mock_repo = MagicMock()
        mock_repo.save_message = AsyncMock()

        session = ChatSession(
            rag=mock_rag, bot=mock_bot,
            repo=mock_repo, room_id="star",
        )
        async for _ in session.handle_message_stream("测试"):
            pass

        assert mock_repo.save_message.call_count == 2
        mock_repo.save_message.assert_any_call("star", "user", "测试")
        mock_repo.save_message.assert_any_call("star", "model", "你好")


# ── LiveRoom 测试 ─────────────────────────────────────────────────────

class TestLiveRoom:
    """测试 LiveRoom 封装。"""

    def test_room_info(self) -> None:
        """info() 应返回房间 ID 和在线人数。"""
        mock_session = MagicMock(spec=ChatSession)
        room = LiveRoom(room_id="star", session=mock_session)

        info = room.info()

        assert info["room_id"] == "star"
        assert info["online_count"] == 0

    def test_online_count_reflects_connections(self) -> None:
        """online_count 应反映连接管理器的连接数。"""
        mock_session = MagicMock(spec=ChatSession)
        room = LiveRoom(room_id="test", session=mock_session)

        room.manager.active_connections = [MagicMock(), MagicMock()]

        assert room.online_count == 2


# ── LiveService 工厂测试 ──────────────────────────────────────────────

class TestLiveService:
    """测试 LiveService 的会话和房间管理能力。"""

    @pytest.mark.asyncio
    async def test_get_room_creates_room_lazily(self) -> None:
        """首次 get_room 应创建新房间，再次调用返回同一实例。"""
        service = LiveService.__new__(LiveService)
        service.rag = MagicMock()
        service._rooms = {}
        service.repo = MagicMock()
        service.repo.get_history = AsyncMock(return_value=[])

        room_a = await service.get_room("star")
        room_b = await service.get_room("star")

        assert room_a is room_b
        assert room_a.room_id == "star"

    @pytest.mark.asyncio
    async def test_get_room_different_ids_independent(self) -> None:
        """不同 room_id 应返回不同的独立房间。"""
        service = LiveService.__new__(LiveService)
        service.rag = MagicMock()
        service._rooms = {}
        service.repo = MagicMock()
        service.repo.get_history = AsyncMock(return_value=[])

        room_star = await service.get_room("star")
        room_moon = await service.get_room("moon")

        assert room_star is not room_moon
        assert room_star.session is not room_moon.session

    @pytest.mark.asyncio
    async def test_list_rooms(self) -> None:
        """list_rooms 应返回所有已创建房间的摘要。"""
        service = LiveService.__new__(LiveService)
        service.rag = MagicMock()
        service._rooms = {}
        service.repo = MagicMock()
        service.repo.get_history = AsyncMock(return_value=[])

        await service.get_room("star")
        await service.get_room("moon")

        rooms = service.list_rooms()
        room_ids = [r["room_id"] for r in rooms]

        assert len(rooms) == 2
        assert "star" in room_ids
        assert "moon" in room_ids

    def test_create_session_returns_independent_sessions(self) -> None:
        """create_session 每次应返回不同的 ChatSession 实例。"""
        service = LiveService.__new__(LiveService)
        service.rag = MagicMock()
        service._rooms = {}

        mock_bot_a = MagicMock()
        mock_bot_b = MagicMock()

        session_a = service.create_session(bot=mock_bot_a)
        session_b = service.create_session(bot=mock_bot_b)

        assert session_a is not session_b
        assert session_a.rag is session_b.rag
        assert session_a.bot is mock_bot_a
        assert session_b.bot is mock_bot_b

    @pytest.mark.asyncio
    async def test_get_room_restores_history(self) -> None:
        """get_room 应从 repo 加载历史并传给 bot。"""
        service = LiveService.__new__(LiveService)
        service.rag = MagicMock()
        service._rooms = {}
        service.repo = MagicMock()
        service.repo.get_history = AsyncMock(return_value=[
            {"role": "user", "content": "你好"},
            {"role": "model", "content": "你好喵~"},
        ])

        room = await service.get_room("star")

        # 验证 repo 被调用了一次
        service.repo.get_history.assert_called_once()
        assert room.room_id == "star"
        # session 应关联了 repo 和 room_id
        assert room.session.repo is service.repo
        assert room.session.room_id == "star"
