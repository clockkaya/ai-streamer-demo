"""
app.services.live_service
~~~~~~~~~~~~~~~~~~~~~~~~~

直播间业务服务 —— 全局单例，管理所有直播间的生命周期。

使用 ``get_live_service()`` 获取单例（懒初始化，import 安全）。
"""
from __future__ import annotations

import os

from app.core.config import settings
from app.core.logging import get_logger
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


class LiveService:
    """直播间业务服务（全局单例）。

    持有共享的 RAG 知识库，管理多个直播间。

    - ``get_room(room_id)`` → 获取/创建指定房间（懒初始化）
    - ``list_rooms()``      → 列出所有活跃房间
    - ``create_session()``  → 创建一次性独立会话（HTTP 无状态用）

    Attributes:
        rag: 共享的向量知识库实例（只读，线程安全）。
    """

    def __init__(self, rag: FAISSKnowledgeBase | None = None) -> None:
        self.rag: FAISSKnowledgeBase = rag or FAISSKnowledgeBase()
        self._rooms: dict[str, LiveRoom] = {}

        # 启动时加载知识库到内存（全局一次）
        knowledge_path: str = _resolve_knowledge_path()
        logger.debug("知识库路径 -> %s", knowledge_path)
        self.rag.load_corpus(knowledge_path)

    def get_room(self, room_id: str) -> LiveRoom:
        """获取指定直播间（不存在则自动创建）。

        Args:
            room_id: 房间唯一标识。

        Returns:
            对应的 ``LiveRoom`` 实例。
        """
        if room_id not in self._rooms:
            session = ChatSession(
                rag=self.rag,
                bot=AIStreamerBot(system_prompt=STREAMER_SYSTEM_PROMPT),
            )
            self._rooms[room_id] = LiveRoom(room_id=room_id, session=session)
            logger.info("直播间已创建 | room_id=%s", room_id)
        return self._rooms[room_id]

    def list_rooms(self) -> list[dict]:
        """列出所有活跃房间的摘要信息。"""
        return [room.info() for room in self._rooms.values()]

    def create_session(self, bot: AIStreamerBot | None = None) -> ChatSession:
        """为单次请求创建独立的聊天会话（HTTP 无状态用）。"""
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
