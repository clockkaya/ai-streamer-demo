"""
app.llm.gemini_bot
~~~~~~~~~~~~~~~~~~

纯 LLM 客户端封装 —— 只负责与 Google Gemini API 的连接和调用。

不包含任何 RAG 检索或 Prompt 组装逻辑（这些职责属于 ``LiveService``）。
通过构造函数接受 ``system_prompt`` 参数实现依赖注入，方便测试和替换。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.client import create_gemini_client

logger = get_logger(__name__)


class AIStreamerBot:
    """Gemini 聊天机器人封装，持有一个异步聊天 Session。

    Attributes:
        model_name: 使用的 Gemini 模型名称。
        system_prompt: 传递给模型的系统级指令。
    """

    def __init__(
        self,
        system_prompt: str,
        model_name: str | None = None,
        client: genai.Client | None = None,
        history: list[types.Content] | None = None,
    ) -> None:
        """初始化聊天机器人。

        Args:
            system_prompt: 系统 Prompt，定义 AI 人设和行为规则。
            model_name: Gemini 模型名称，默认读取 ``settings.GEMINI_MODEL``。
            client: 可选的 ``genai.Client`` 实例（用于测试注入 mock）。
            history: 可选的对话历史，用于恢复之前的对话上下文。
        """
        self.model_name: str = model_name or settings.GEMINI_MODEL
        self.system_prompt: str = system_prompt
        self._client: genai.Client = client or create_gemini_client()

        # 创建异步聊天 Session，注入 system_prompt 和可选的对话历史
        self.chat_session = self._client.aio.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
            ),
            history=history or [],
        )
        if history:
            logger.info(
                "LLM 客户端已初始化（含 %d 条历史）| model=%s",
                len(history), self.model_name,
            )
        else:
            logger.info("LLM 客户端已初始化 | model=%s", self.model_name)

    async def generate_reply(self, prompt: str) -> str:
        """发送消息并获取完整回复（非流式）。

        Args:
            prompt: 发送给模型的完整 Prompt（已由上层组装好）。

        Returns:
            模型的完整回复文本。发生异常时返回用户友好的错误提示。
        """
        try:
            response = await self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            logger.error("LLM 调用异常: %s", e, exc_info=True)
            return f"哎呀，直播间线路好像卡了一下... (错误信息: {e!s})"

    async def generate_reply_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """发送消息并以异步生成器逐字返回回复（流式）。

        Args:
            prompt: 发送给模型的完整 Prompt（已由上层组装好）。

        Yields:
            模型回复中的每一个字符。
        """
        try:
            response_stream = await self.chat_session.send_message_stream(prompt)
            async for chunk in response_stream:
                if chunk.text:
                    # 逐字 yield，实现打字机效果
                    for char in chunk.text:
                        yield char
        except Exception as e:
            logger.error("LLM 流式调用异常: %s", e, exc_info=True)
            yield f"哎呀，直播间线路好像卡了一下... (错误信息: {e!s})"