from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 项目基础配置
    PROJECT_NAME: str = "AI Streamer Backend"
    VERSION: str = "0.1.0"

    # 核心 API Key (Pydantic 会自动从 .env 文件中读取同名变量)
    GEMINI_API_KEY: str

    # 指定加载 .env 文件
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# 实例化配置对象，供全局调用
settings = Settings()