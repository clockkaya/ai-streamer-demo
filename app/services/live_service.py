"""
app.services.live_service
~~~~~~~~~~~~~~~~~~~~~~~~~

直播间业务服务 —— 全局单例，管理所有直播间的生命周期。

使用 ``get_live_service()`` 获取单例（懒初始化，import 安全）。
"""
from __future__ import annotations

import os

from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.db import get_database
from app.db.chat_repository import ChatRepository
from app.llm.gemini_bot import AIStreamerBot
from app.prompts.streamer import STREAMER_SYSTEM_PROMPT
from app.rag.vector_store import FAISSKnowledgeBase
from app.services.room import LiveRoom
from app.services.session import ChatSession

logger = get_logger(__name__)


def _resolve_knowledge_path() -> str:
    """解析知识库文件的绝对路径。"""
    base_dir: str = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return os.path.join(base_dir, settings.KNOWLEDGE_FILE)


def _messages_to_history(messages: list[dict]) -> list[types.Content]:
    """将 MongoDB 消息记录转换为 Gemini Content 对象列表。

    Args:
        messages: 从 ChatRepository 获取的消息字典列表。

    Returns:
        可传入 ``AIStreamerBot(history=...)`` 的 Content 列表。
    """
    history: list[types.Content] = []
    for msg in messages:
        history.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])],
            ),
        )
    return history


class LiveService:
    """直播间业务服务（全局单例）。

    持有共享的 RAG 知识库和 ChatRepository，管理多个直播间。

    - ``get_room(room_id)`` → 获取/创建指定房间（懒初始化，含历史恢复）
    - ``list_rooms()``      → 列出所有活跃房间
    - ``create_session()``  → 创建一次性独立会话（HTTP 无状态用）

    Attributes:
        rag: 共享的向量知识库实例（只读，线程安全）。
        repo: 对话持久化仓库。
    """

    def __init__(self, rag: FAISSKnowledgeBase | None = None) -> None:
        self.rag: FAISSKnowledgeBase = rag or FAISSKnowledgeBase()
        self.repo: ChatRepository = ChatRepository(get_database())
        self._rooms: dict[str, LiveRoom] = {}

        # 启动时加载知识库到内存（全局一次）
        knowledge_path: str = _resolve_knowledge_path()
        logger.debug("知识库路径 -> %s", knowledge_path)
        self.rag.load_corpus(knowledge_path)

    async def get_room(self, room_id: str) -> LiveRoom:
        """获取指定直播间（不存在则自动创建，并从 MongoDB 恢复对话上下文）。

        Args:
            room_id: 房间唯一标识。

        Returns:
            对应的 ``LiveRoom`` 实例。
        """
        if room_id not in self._rooms:
            # 从 MongoDB 加载历史消息
            messages = await self.repo.get_history(
                room_id, limit=settings.CHAT_HISTORY_LIMIT,
            )
            history = _messages_to_history(messages)

            bot = AIStreamerBot(
                system_prompt=STREAMER_SYSTEM_PROMPT,
                history=history if history else None,
            )
            session = ChatSession(
                rag=self.rag,
                bot=bot,
                repo=self.repo,
                room_id=room_id,
            )
            self._rooms[room_id] = LiveRoom(room_id=room_id, session=session)
            logger.info(
                "直播间已创建 | room_id=%s | 恢复 %d 条历史",
                room_id, len(messages),
            )
        return self._rooms[room_id]

    def list_rooms(self) -> list[dict]:
        """列出所有活跃房间的摘要信息。"""
        return [room.info() for room in self._rooms.values()]

    def create_session(self, bot: AIStreamerBot | None = None) -> ChatSession:
        """为单次请求创建独立的聊天会话（HTTP 无状态用，不持久化）。"""
        session_bot: AIStreamerBot = bot or AIStreamerBot(
            system_prompt=STREAMER_SYSTEM_PROMPT,
        )
        return ChatSession(rag=self.rag, bot=session_bot)


# ---------------------------------------------------------------------------
# 懒初始化单例
# ---------------------------------------------------------------------------
_live_service: LiveService | None = None


def get_live_service() -> LiveService:
    """获取全局 LiveService 单例（懒初始化）。"""
    global _live_service
    if _live_service is None:
        _live_service = LiveService()
    return _live_service
