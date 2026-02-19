"""
app.core.config
~~~~~~~~~~~~~~~

集中式配置管理，基于 pydantic-settings 自动从 ``.env`` 文件加载。

支持通过 ``ENVIRONMENT`` 变量区分 **development** / **testing** / **production** 环境，
所有散落在各模块中的硬编码值（模型名、TTS 声音、知识库路径等）统一收拢至此。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """全局配置对象，字段值按如下优先级加载：环境变量 > .env 文件 > 默认值。"""

    # ── 基础 ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = Field(default="AI Streamer Backend", description="项目名称")
    VERSION: str = Field(default="0.1.0", description="版本号")
    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        default="development",
        description="运行环境：development / testing / production",
    )

    # ── API Keys ──────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")

    # ── LLM ───────────────────────────────────────────────────────────
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini 聊天模型名称",
    )
    EMBEDDING_MODEL: str = Field(
        default="gemini-embedding-001",
        description="Gemini Embedding 模型名称",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=3072,
        description="Embedding 向量维度",
    )

    # ── TTS ────────────────────────────────────────────────────────────
    TTS_VOICE: str = Field(
        default="zh-CN-XiaoyiNeural",
        description="Edge-TTS 语音模型",
    )

    # ── RAG / 数据 ────────────────────────────────────────────────────
    KNOWLEDGE_FILE: str = Field(
        default="data/knowledge.txt",
        description="知识库文本文件的相对路径（相对项目根目录）",
    )

    # ── 服务 ──────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    PORT: int = Field(default=8000, description="服务监听端口")
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")

    # ── Pydantic Settings ─────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 便捷属性 ──────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        """当前是否为生产环境。"""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """当前是否为测试环境。"""
        return self.ENVIRONMENT == "testing"

    @property
    def debug(self) -> bool:
        """非生产环境默认开启 debug 模式。"""
        return not self.is_production

@lru_cache
def get_settings() -> Settings:
    """获取全局 Settings 单例（带缓存，避免重复解析 .env）。"""
    return Settings()

# 保留向后兼容的全局变量
settings: Settings = get_settings()