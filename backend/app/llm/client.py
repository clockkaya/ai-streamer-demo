"""
app.llm.client
~~~~~~~~~~~~~~

Gemini API 客户端工厂 —— 全局共享的客户端创建入口。

所有需要 Gemini Client 的模块（LLM 聊天、Embedding）统一从此处获取，
避免重复的 ``_create_client()`` 实现分散在各模块中。
"""
from __future__ import annotations

from google import genai

from app.core.settings import settings


def create_gemini_client() -> genai.Client:
    """创建 Gemini API 客户端实例。

    Returns:
        已认证的 ``genai.Client``。
    """
    return genai.Client(api_key=settings.GEMINI_API_KEY)
