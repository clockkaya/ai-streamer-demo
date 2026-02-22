"""
app.db.chat_repository
~~~~~~~~~~~~~~~~~~~~~~

对话记录持久化仓库 —— 封装 MongoDB ``chat_messages`` 集合的增查操作。

每条消息一个文档（扁平设计），避免 16MB 文档限制且便于分页查询。
集合在首次写入时自动创建并建立索引。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.logging import get_logger
from app.schemas.live_interactions import MessageRole

logger = get_logger(__name__)

# 集合名称
_COLLECTION_NAME = "chat_messages"

class ChatMessage(TypedDict):
    """代表 MongoDB 中 chat_messages 集合的单条记录"""
    room_id: str
    role: MessageRole
    content: str
    created_at: datetime


class ChatRepository:
    """对话消息持久化仓库。

    Attributes:
        db: MongoDB 数据库实例。
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self._collection = db[_COLLECTION_NAME]
        self._indexes_created = False

    async def _ensure_indexes(self) -> None:
        """确保索引已创建（惰性，首次操作时执行一次）。"""
        if self._indexes_created:
            return
        # 复合索引：按房间分区 + 按时间排序
        await self._collection.create_index(
            [("room_id", 1), ("created_at", 1)],
            name="idx_room_time",
        )
        self._indexes_created = True
        logger.debug("chat_messages 索引已就绪")

    async def save_message(
        self,
        room_id: str,
        role: MessageRole,
        content: str,
    ) -> None:
        """保存一条对话消息。

        Args:
            room_id: 房间唯一标识。
            role: 消息角色，``"user"`` 或 ``"model"``。
            content: 消息文本内容。
        """
        await self._ensure_indexes()
        doc = {
            "room_id": room_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc),
        }
        await self._collection.insert_one(doc)

    async def get_history(
        self,
        room_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """获取指定房间的最近 N 条消息（按时间正序）。

        用于恢复 Gemini chat session 上下文。

        Args:
            room_id: 房间唯一标识。
            limit: 最大返回条数。

        Returns:
            消息字典列表，每条包含 ``role``、``content``、``created_at``。
        """
        await self._ensure_indexes()

        # 先按时间倒序取最近 N 条，再反转为正序
        cursor = (
            self._collection
            .find(
                {"room_id": room_id},
                {"_id": 0, "role": 1, "content": 1, "created_at": 1},
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        messages = await cursor.to_list(length=limit)
        messages.reverse()
        return messages

    async def get_all_messages(
        self,
        room_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """获取指定房间的全部消息（分页，用于历史回看）。

        Args:
            room_id: 房间唯一标识。
            skip: 跳过条数（分页偏移）。
            limit: 每页最大条数。

        Returns:
            消息字典列表，按时间正序。
        """
        await self._ensure_indexes()
        cursor = (
            self._collection
            .find(
                {"room_id": room_id},
                {"_id": 0, "room_id": 1, "role": 1, "content": 1, "created_at": 1},
            )
            .sort("created_at", 1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_messages(self, room_id: str) -> int:
        """获取指定房间的消息总数。"""
        await self._ensure_indexes()
        return await self._collection.count_documents({"room_id": room_id})
