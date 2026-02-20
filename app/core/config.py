"""
app.core.config
~~~~~~~~~~~~~~~

集中式配置管理，基于 pydantic-settings 自动从 ``.env`` 文件加载。

支持多环境配置（dev / test / prod），加载顺序为:
  1. 环境变量（最高优先级）
  2. ``.env.{ENVIRONMENT}`` 环境专属文件
  3. ``.env`` 基础文件
  4. 字段默认值（最低优先级）
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 读取当前环境标识（在 Settings 类定义之前，用于决定加载哪个 .env 文件）
_CURRENT_ENV: str = os.getenv("ENVIRONMENT", "dev")


class Settings(BaseSettings):
    """全局配置对象，字段值按如下优先级加载：环境变量 > .env.{env} > .env > 默认值。"""

    # ── 基础 ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = Field(default="AI Streamer Backend", description="项目名称")
    VERSION: str = Field(default="0.1.0", description="版本号")
    ENVIRONMENT: Literal["dev", "test", "prod"] = Field(
        default="dev",
        description="运行环境：dev / test / prod",
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
    LOG_LEVEL: str = Field(default="INFO", description="日志级别（可被环境属性覆盖）")

    # ── Pydantic Settings ─────────────────────────────────────────────
    # 先加载 .env.{env} 再加载 .env，前者优先级更高
    model_config = SettingsConfigDict(
        env_file=(f".env.{_CURRENT_ENV}", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 环境判断 ──────────────────────────────────────────────────────

    @property
    def is_prod(self) -> bool:
        """当前是否为生产环境。"""
        return self.ENVIRONMENT == "prod"

    @property
    def is_test(self) -> bool:
        """当前是否为测试环境。"""
        return self.ENVIRONMENT == "test"

    @property
    def is_dev(self) -> bool:
        """当前是否为开发环境。"""
        return self.ENVIRONMENT == "dev"

    # ── 环境差异化行为 ────────────────────────────────────────────────

    @property
    def debug(self) -> bool:
        """是否开启 debug 模式。仅 dev 环境开启。"""
        return self.is_dev

    @property
    def reload(self) -> bool:
        """是否开启热重载。仅 dev 环境开启。"""
        return self.is_dev

    @property
    def effective_log_level(self) -> str:
        """根据环境自动推断日志级别。

        - dev  → DEBUG（方便调试）
        - test → DEBUG（方便排查测试失败）
        - prod → WARNING（减少噪音）

        如果 .env 中显式设置了 LOG_LEVEL，会覆盖此默认推断。
        """
        # 如果用户未在环境变量中显式设置 LOG_LEVEL，使用环境推断值
        env_log = os.getenv("LOG_LEVEL")
        if env_log:
            return env_log
        return {
            "dev": "INFO",
            "test": "DEBUG",
            "prod": "WARNING",
        }.get(self.ENVIRONMENT, "INFO")

    @property
    def allow_cors_all_origins(self) -> bool:
        """是否允许所有 CORS 来源。非 prod 环境允许，方便本地调试。"""
        return not self.is_prod


@lru_cache
def get_settings() -> Settings:
    """获取全局 Settings 单例（带缓存，避免重复解析 .env）。"""
    return Settings()


# 保留向后兼容的全局变量
settings: Settings = get_settings()