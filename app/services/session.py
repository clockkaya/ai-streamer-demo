"""
app.services.session
~~~~~~~~~~~~~~~~~~~~

聊天会话领域模型 —— 封装单次 LLM 对话的 RAG 检索 + Prompt 组装 + 调用流程。

``ChatSession`` 可被多个 WebSocket 连接共享（直播间模式），
也可作为一次性会话使用（HTTP 模式）。

当关联了 ``ChatRepository`` 时，会自动将对话消息持久化到 MongoDB。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from app.core.logging import get_logger
from app.db.chat_repository import ChatRepository
from app.llm.gemini_bot import AIStreamerBot
from app.prompts.streamer import build_rag_prompt
from app.rag.vector_store import FAISSKnowledgeBase

logger = get_logger(__name__)


class ChatSession:
    """单个聊天会话，持有独立的 LLM 对话 Session。

    Attributes:
        bot: 本会话的 AI 聊天机器人实例。
        rag: 共享的向量知识库引用（只读）。
        repo: 可选的对话持久化仓库（为 None 时不持久化）。
        room_id: 关联的房间 ID（持久化时使用）。
    """

    def __init__(
        self,
        rag: FAISSKnowledgeBase,
        bot: AIStreamerBot,
        repo: ChatRepository | None = None,
        room_id: str | None = None,
    ) -> None:
        self.rag = rag
        self.bot = bot
        self.repo = repo
        self.room_id = room_id

    async def handle_message(self, user_message: str) -> str:
        """处理观众弹幕并返回完整回复（非流式）。"""
        final_prompt: str = self._build_prompt(user_message)
        reply: str = await self.bot.generate_reply(final_prompt)

        # 持久化对话记录
        await self._persist(user_message, reply)

        return reply

    async def handle_message_stream(
        self, user_message: str,
    ) -> AsyncGenerator[str, None]:
        """处理观众弹幕并以流式方式逐字返回回复。"""
        final_prompt: str = self._build_prompt(user_message)
        full_reply: str = ""
        async for char in self.bot.generate_reply_stream(final_prompt):
            full_reply += char
            yield char

        # 流式结束后持久化
        await self._persist(user_message, full_reply)

    def _build_prompt(self, user_message: str) -> str:
        """执行 RAG 检索并组装最终 Prompt。"""
        reference_knowledge: str = self.rag.search(user_message)
        if reference_knowledge:
            logger.info("RAG 命中: %s", reference_knowledge[:80])
        return build_rag_prompt(user_message, reference_knowledge)

    async def _persist(self, user_message: str, bot_reply: str) -> None:
        """将一轮对话（用户 + 模型）保存到 MongoDB。"""
        if self.repo is None or self.room_id is None:
            return
        try:
            await self.repo.save_message(self.room_id, "user", user_message)
            await self.repo.save_message(self.room_id, "model", bot_reply)
        except Exception as e:
            # 持久化失败不应阻塞对话流程
            logger.warning("对话持久化失败: %s", e, exc_info=True)
