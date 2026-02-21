"""
app.services.live_room
~~~~~~~~~~~~~~~~~

直播间领域模型 —— 封装一个完整的直播间实体。

每个 ``LiveRoom`` 拥有独立的 LLM 对话历史（``BotContext``）
和观众列表（``RoomBroadcaster``），房间之间互不干扰。
"""
from __future__ import annotations

from app.schemas.live_interactions import RoomInfoData
from app.services.room_broadcaster import RoomBroadcaster
from app.services.bot_context import BotContext


class LiveRoom:
    """一个完整的直播间实体。

    Attributes:
        room_id: 房间唯一标识。
        persona_id: 正在使用的主播人设 ID。
        bot_context: 本房间的共享聊天会话。
        broadcaster: 本房间的连接管理器。
    """

    def __init__(self, room_id: str, persona_id: str, bot_context: BotContext) -> None:
        self.room_id = room_id
        self.persona_id = persona_id
        self.bot_context = bot_context
        self.broadcaster = RoomBroadcaster()

    @property
    def online_count(self) -> int:
        """当前在线观众数。"""
        return self.broadcaster.online_count

    def info(self) -> RoomInfoData:
        """返回房间摘要信息。"""
        return RoomInfoData(
            room_id=self.room_id,
            persona_id=self.persona_id,
            online_count=self.online_count,
        )
