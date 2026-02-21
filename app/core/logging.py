"""
app.core.logging
~~~~~~~~~~~~~~~~

统一日志配置，根据环境自动设置日志级别和格式。

所有模块应通过 ``get_logger(__name__)`` 获取 logger 实例，
不要直接使用 ``print()`` 输出调试信息。
"""
from __future__ import annotations

import logging
import sys

from app.core.settings import settings

# 日志格式：时间 | 级别 | 模块名 | 消息
_LOG_FORMAT: str = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """根据当前环境配置全局日志。应在应用启动时调用一次。"""
    level = getattr(logging, settings.effective_log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
        stream=sys.stdout,
        force=True,  # 覆盖可能已有的 basicConfig
    )

    # 降低第三方库的日志噪音
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的 logger 实例。

    Args:
        name: 模块名，通常传 ``__name__``。

    Returns:
        配置好的 ``logging.Logger`` 实例。
    """
    return logging.getLogger(name)
