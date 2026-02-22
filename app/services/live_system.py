"""
app.services.live_system
~~~~~~~~~~~~~~~~~~~~~~~~~

直播间业务服务 —— 全局单例，管理所有直播间的生命周期。

使用 ``get_live_system()`` 获取单例（懒初始化，import 安全）。
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.persona import PersonaManager
from app.core.settings import settings
from app.db import get_database
from app.db.chat_repository import ChatRepository
from app.llm.gemini_provider import GeminiProvider
from app.schemas.live_interactions import RoomInfoData
from app.services.bot_context import BotContext
from app.services.live_room import LiveRoom

logger = get_logger(__name__)



class LiveSystem:
    """直播系统（全局单例）。

    持有 ChatRepository 和 PersonaManager，管理多个直播间。

    - ``get_room(room_id, persona_id)`` → 获取/创建指定房间（懒初始化，含历史恢复）
    - ``list_rooms()``                  → 列出所有活跃房间
    - ``create_session(persona_id)``    → 创建一次性独立会话（HTTP 无状态用）

    Attributes:
        repo: 对话持久化仓库。
        pm: 角色包管理器。
    """

    def __init__(self, pm: PersonaManager) -> None:
        self.pm: PersonaManager = pm
        self.repo: ChatRepository = ChatRepository(get_database())
        self._rooms: dict[str, LiveRoom] = {}

    async def get_room(self, room_id: str, persona_id: str | None = None) -> LiveRoom:
        """获取指定直播间（不存在则自动创建，并从 MongoDB 恢复对话上下文）。"""
        if room_id not in self._rooms:
            # 获取对应的角色包
            target_persona = persona_id or self.pm.default_persona_id
            bundle = self.pm.get_bundle(target_persona)

            # 从 MongoDB 加载历史消息
            messages = await self.repo.get_history(
                room_id, limit=settings.CHAT_HISTORY_LIMIT,
            )
            history_dicts = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

            bot = GeminiProvider(
                system_prompt=bundle.config.system_prompt,
                fallback_responses=bundle.config.fallback_responses,
                history=history_dicts if history_dicts else None,
            )
            context = BotContext(
                persona=bundle.config,
                rag=bundle.rag,
                bot=bot,
                repo=self.repo,
                room_id=room_id,
            )
            self._rooms[room_id] = LiveRoom(room_id=room_id, persona_id=target_persona, bot_context=context)
            logger.info(
                "直播间已创建 | room_id=%s | persona=%s | 恢复 %d 条历史",
                room_id, target_persona, len(messages),
            )
        return self._rooms[room_id]

    def list_rooms(self) -> list[RoomInfoData]:
        """列出所有活跃房间的摘要信息。"""
        return [room.info() for room in self._rooms.values()]

    def create_session(self, persona_id: str | None = None, bot: GeminiProvider | None = None) -> BotContext:
        """为单次请求创建独立的聊天会话小脑（HTTP 无状态用，不持久化）。"""
        target_persona = persona_id or self.pm.default_persona_id
        bundle = self.pm.get_bundle(target_persona)
        
        session_bot: GeminiProvider = bot or GeminiProvider(
            system_prompt=bundle.config.system_prompt,
            fallback_responses=bundle.config.fallback_responses,
        )
        return BotContext(persona=bundle.config, rag=bundle.rag, bot=session_bot)


# 移除了全局单例，改为在 FastAPI lifespan 中初始化并挂载于 app.state
