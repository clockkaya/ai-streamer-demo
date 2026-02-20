"""
app.services.chat_service
~~~~~~~~~~~~~~~~~~~~~~~~~

业务服务层 —— 串联 LLM、RAG 和 Prompt 模块。

架构设计:
  - ``ChatService``（单例）持有共享的只读 RAG 知识库
  - ``ChatSession``（每连接一个）持有独立的 LLM 对话 Session

API 路由层通过 ``chat_service.create_session()`` 为每个连接创建独立会话，
避免不同用户的对话上下文互相污染。
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.gemini_bot import AIStreamerBot
from app.prompts.streamer import STREAMER_SYSTEM_PROMPT, build_rag_prompt
from app.rag.vector_store import FAISSKnowledgeBase

logger = get_logger(__name__)


def _resolve_knowledge_path() -> str:
    """解析知识库文件的绝对路径。

    基于 ``settings.KNOWLEDGE_FILE``（相对项目根目录）计算绝对路径。

    Returns:
        知识库文件的绝对路径。
    """
    # 从当前文件向上两级定位到项目根目录
    base_dir: str = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return os.path.join(base_dir, settings.KNOWLEDGE_FILE)


class ChatSession:
    """单个用户的聊天会话，持有独立的 LLM 对话 Session。

    每个 WebSocket 连接或 HTTP 请求应创建各自的 ``ChatSession``，
    确保对话上下文互不干扰。RAG 知识库通过引用共享，不会重复加载。

    Attributes:
        bot: 本会话专属的 AI 聊天机器人实例。
        rag: 共享的向量知识库引用（只读）。
    """

    def __init__(self, rag: FAISSKnowledgeBase, bot: AIStreamerBot) -> None:
        """初始化 ChatSession。

        Args:
            rag: 共享的 ``FAISSKnowledgeBase`` 实例。
            bot: 本会话专属的 ``AIStreamerBot`` 实例。
        """
        self.rag = rag
        self.bot = bot

    async def handle_message(self, user_message: str) -> str:
        """处理观众弹幕并返回完整回复（非流式）。

        流程: 弹幕 → RAG 检索 → Prompt 组装 → LLM 生成 → 返回回复。

        Args:
            user_message: 观众发送的弹幕文本。

        Returns:
            AI 主播的完整回复文本。
        """
        final_prompt: str = self._build_prompt(user_message)
        return await self.bot.generate_reply(final_prompt)

    async def handle_message_stream(
        self, user_message: str,
    ) -> AsyncGenerator[str, None]:
        """处理观众弹幕并以流式方式逐字返回回复。

        流程: 弹幕 → RAG 检索 → Prompt 组装 → LLM 流式生成 → 逐字 yield。

        Args:
            user_message: 观众发送的弹幕文本。

        Yields:
            模型回复中的每一个字符。
        """
        final_prompt: str = self._build_prompt(user_message)
        async for char in self.bot.generate_reply_stream(final_prompt):
            yield char

    def _build_prompt(self, user_message: str) -> str:
        """内部方法：执行 RAG 检索并组装最终 Prompt。

        Args:
            user_message: 观众发送的弹幕文本。

        Returns:
            组装后的 Prompt 字符串。
        """
        # 先从共享向量库中检索相关知识
        reference_knowledge: str = self.rag.search(user_message)
        if reference_knowledge:
            logger.info("RAG 命中: %s", reference_knowledge[:80])
        # 将检索结果和用户消息组装为最终 Prompt
        return build_rag_prompt(user_message, reference_knowledge)


class ChatService:
    """直播间聊天业务服务（全局单例）。

    持有共享的 RAG 知识库，通过 ``create_session()`` 为每个连接
    创建独立的 ``ChatSession``（各自拥有独立的 LLM 对话上下文）。

    Attributes:
        rag: 共享的向量知识库实例（只读，线程安全）。
    """

    def __init__(self, rag: FAISSKnowledgeBase | None = None) -> None:
        """初始化 ChatService，加载共享 RAG 知识库。

        Args:
            rag: 可选的 ``FAISSKnowledgeBase`` 实例（用于测试注入 mock）。
        """
        self.rag: FAISSKnowledgeBase = rag or FAISSKnowledgeBase()

        # 启动时加载知识库到内存（全局一次）
        knowledge_path: str = _resolve_knowledge_path()
        logger.debug("知识库路径 -> %s", knowledge_path)
        self.rag.load_corpus(knowledge_path)

    def create_session(self, bot: AIStreamerBot | None = None) -> ChatSession:
        """为新连接创建独立的聊天会话。

        每次调用都会创建一个全新的 ``AIStreamerBot``（独立的 Gemini chat session），
        确保不同用户的对话上下文完全隔离。

        Args:
            bot: 可选的 ``AIStreamerBot`` 实例（用于测试注入 mock）。

        Returns:
            新的 ``ChatSession`` 实例。
        """
        session_bot: AIStreamerBot = bot or AIStreamerBot(
            system_prompt=STREAMER_SYSTEM_PROMPT,
        )
        logger.debug("创建新会话 | bot_model=%s", session_bot.model_name)
        return ChatSession(rag=self.rag, bot=session_bot)


# ---------------------------------------------------------------------------
# 全局单例 —— 应用启动时初始化（只加载一次 RAG）
# ---------------------------------------------------------------------------
chat_service: ChatService = ChatService()
