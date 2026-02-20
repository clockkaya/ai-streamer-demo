"""
app.services.chat_service
~~~~~~~~~~~~~~~~~~~~~~~~~

业务服务层 —— 串联 LLM、RAG 和 Prompt 模块。

架构设计:
  - ``ChatService``（单例，懒初始化）持有共享的 RAG 知识库
  - ``ChatSession``（按需创建）持有独立的 LLM 对话 Session
  - WebSocket 模式：所有连接共享一个 ChatSession（直播间共享上下文）
  - HTTP 模式：每次请求创建一次性 ChatSession（无状态）

注意: 使用 ``get_chat_service()`` 获取单例，而非直接导入模块级变量。
这确保了测试时可以安全 import 本模块而不触发真实 API 调用。
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
    """单个聊天会话，持有独立的 LLM 对话 Session。

    可被多个 WebSocket 连接共享（直播间模式），也可作为一次性会话使用（HTTP 模式）。
    RAG 知识库通过引用共享，不会重复加载。

    Attributes:
        bot: 本会话的 AI 聊天机器人实例。
        rag: 共享的向量知识库引用（只读）。
    """

    def __init__(self, rag: FAISSKnowledgeBase, bot: AIStreamerBot) -> None:
        """初始化 ChatSession。

        Args:
            rag: 共享的 ``FAISSKnowledgeBase`` 实例。
            bot: 本会话的 ``AIStreamerBot`` 实例。
        """
        self.rag = rag
        self.bot = bot

    async def handle_message(self, user_message: str) -> str:
        """处理观众弹幕并返回完整回复（非流式）。

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

        Args:
            user_message: 观众发送的弹幕文本。

        Yields:
            模型回复中的每一个字符。
        """
        final_prompt: str = self._build_prompt(user_message)
        async for char in self.bot.generate_reply_stream(final_prompt):
            yield char

    def _build_prompt(self, user_message: str) -> str:
        """内部方法：执行 RAG 检索并组装最终 Prompt。"""
        # 先从共享向量库中检索相关知识
        reference_knowledge: str = self.rag.search(user_message)
        if reference_knowledge:
            logger.info("RAG 命中: %s", reference_knowledge[:80])
        # 将检索结果和用户消息组装为最终 Prompt
        return build_rag_prompt(user_message, reference_knowledge)


class ChatService:
    """直播间聊天业务服务。

    持有共享的 RAG 知识库，提供两种会话模式：

    - ``get_live_session()`` → 返回直播间共享会话（所有 WS 连接共用同一上下文）
    - ``create_session()``   → 创建一次性独立会话（HTTP 无状态请求用）

    Attributes:
        rag: 共享的向量知识库实例（只读，线程安全）。
    """

    def __init__(self, rag: FAISSKnowledgeBase | None = None) -> None:
        self.rag: FAISSKnowledgeBase = rag or FAISSKnowledgeBase()
        self._live_session: ChatSession | None = None

        # 启动时加载知识库到内存（全局一次）
        knowledge_path: str = _resolve_knowledge_path()
        logger.debug("知识库路径 -> %s", knowledge_path)
        self.rag.load_corpus(knowledge_path)

    def get_live_session(self) -> ChatSession:
        """获取直播间共享会话（懒初始化单例）。

        所有 WebSocket 连接共用同一个 LLM 对话上下文，
        模拟真实直播间：主播能看到所有观众的弹幕并在同一上下文中回应。
        """
        if self._live_session is None:
            self._live_session = ChatSession(
                rag=self.rag,
                bot=AIStreamerBot(system_prompt=STREAMER_SYSTEM_PROMPT),
            )
            logger.info("直播间会话已创建")
        return self._live_session

    def create_session(self, bot: AIStreamerBot | None = None) -> ChatSession:
        """为单次请求创建独立的聊天会话（HTTP 无状态用）。"""
        session_bot: AIStreamerBot = bot or AIStreamerBot(
            system_prompt=STREAMER_SYSTEM_PROMPT,
        )
        return ChatSession(rag=self.rag, bot=session_bot)


# ---------------------------------------------------------------------------
# 懒初始化单例 —— 仅在首次调用 get_chat_service() 时创建，
# import 本模块不会触发任何 API 调用（测试安全）。
# ---------------------------------------------------------------------------
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """获取全局 ChatService 单例（懒初始化）。"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
