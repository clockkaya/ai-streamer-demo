"""
app.services.room
~~~~~~~~~~~~~~~~~

直播间领域模型 —— 封装一个完整的直播间实体。

每个 ``LiveRoom`` 拥有独立的 LLM 对话历史（``ChatSession``）
和观众列表（``ConnectionManager``），房间之间互不干扰。
"""
from __future__ import annotations

from app.services.connection import ConnectionManager
from app.services.session import ChatSession


class LiveRoom:
    """一个完整的直播间实体。

    Attributes:
        room_id: 房间唯一标识。
        session: 本房间的共享聊天会话。
        manager: 本房间的连接管理器。
    """

    def __init__(self, room_id: str, session: ChatSession) -> None:
        self.room_id = room_id
        self.session = session
        self.manager = ConnectionManager()

    @property
    def online_count(self) -> int:
        """当前在线观众数。"""
        return self.manager.online_count

    def info(self) -> dict:
        """返回房间摘要信息。"""
        return {
            "room_id": self.room_id,
            "online_count": self.online_count,
        }
