"""
app.core.rate_limit
~~~~~~~~~~~~

API 与 WebSocket 的限流配置。
"""
import time
from typing import Dict

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

import threading
from collections import Counter, defaultdict
from limits.storage.memory import MemoryStorage
from limits.storage.base import Storage

class SafeMemoryStorage(MemoryStorage):
    """
    延迟启动 timer 线程的内存存储后端。
    解决在 Windows 系统中 uvicorn --reload 模式下由于 multiprocessing.spawn 阶段启动线程导致的 hang/死锁问题。
    """
    STORAGE_SCHEME = ["safe-memory"]

    def __init__(self, uri: str | None = None, wrap_exceptions: bool = False, **kwargs: str):
        # 初始化需要的字典，但不在这里调用 self.timer.start()
        self.storage = Counter()
        self.locks = defaultdict(threading.RLock)
        self.expirations = {}
        self.events = {}
        self.timer = threading.Timer(0.01, self._MemoryStorage__expire_events)
        Storage.__init__(self, uri, wrap_exceptions=wrap_exceptions, **kwargs)


# --------- HTTP 接口限流器 ---------
# 基于客户端 IP 地址进行限流
# 💡 使用自定义延迟线程的 "safe-memory://" 存储方案，避免在 Windows 系统的 reload 模式下因自动探测引起的线程死锁。
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="safe-memory://",
)


# --------- WebSocket 限流器 ---------
class WebSocketRateLimiter:
    """基于内存的简单 WebSocket 弹幕限流器。
    
    记录每个 WebSocket 连接（或特定标识）上一次发送消息的时间。
    如果过快请求，则拒绝。
    """
    def __init__(self, interval_seconds: float = 2.0):
        self.interval_seconds = interval_seconds
        # key 可是 ws 对象 id(id(websocket)) 或者 user id
        self._last_message_time: Dict[int, float] = {}

    def is_allowed(self, client_id: int) -> bool:
        """检查客户端是否允许发送消息。
        
        Args:
            client_id: 客户端唯一标识（如 id(websocket)）
            
        Returns:
            是否允许发送。如果允许，则同时更新上次发送时间。
        """
        now = time.time()
        last_time = self._last_message_time.get(client_id, 0.0)
        
        if now - last_time >= self.interval_seconds:
            self._last_message_time[client_id] = now
            return True
        return False

    def remove_client(self, client_id: int) -> None:
        """清理断开连接的客户端记录。"""
        self._last_message_time.pop(client_id, None)
