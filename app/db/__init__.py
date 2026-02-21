"""
app.db.__init__
~~~~~~

MongoDB 异步连接管理。

使用 ``motor`` 提供的 ``AsyncIOMotorClient``，在应用生命周期内维护一个
全局连接池。启动时调用 ``connect_mongo()``，关闭时调用 ``close_mongo()``。
"""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None


def _mask_uri(uri: str) -> str:
    """将 MongoDB URI 中的密码替换为 ``***``，防止日志泄漏凭证。"""
    parsed = urlparse(uri)
    if parsed.password:
        masked = parsed._replace(
            netloc=f"{parsed.username}:***@{parsed.hostname}"
            + (f":{parsed.port}" if parsed.port else ""),
        )
        return urlunparse(masked)
    return uri


async def connect_mongo() -> None:
    """初始化 MongoDB 连接池。应在 lifespan startup 中调用。"""
    global _client
    _client = AsyncIOMotorClient(settings.MONGO_URI)

    # 验证连接 + 认证：对目标数据库执行 ping（需要认证才能通过）
    try:
        db = _client[settings.MONGO_DB_NAME]
        await db.command("ping")
        logger.info(
            "MongoDB 已连接 | uri=%s | db=%s",
            _mask_uri(settings.MONGO_URI),
            settings.MONGO_DB_NAME,
        )
    except Exception as e:
        logger.error("MongoDB 连接失败: %s", e, exc_info=True)
        raise


async def close_mongo() -> None:
    """关闭 MongoDB 连接池。应在 lifespan shutdown 中调用。"""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB 连接已关闭")


def get_database() -> AsyncIOMotorDatabase:
    """获取默认数据库实例。

    Returns:
        ``AsyncIOMotorDatabase`` 实例。

    Raises:
        RuntimeError: 如果在 ``connect_mongo()`` 之前调用。
    """
    if _client is None:
        raise RuntimeError(
            "MongoDB 尚未初始化，请先调用 connect_mongo()",
        )
    return _client[settings.MONGO_DB_NAME]
