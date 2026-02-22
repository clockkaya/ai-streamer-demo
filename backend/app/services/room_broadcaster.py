"""
app.services.room_broadcaster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

WebSocket 连接广播器 —— 维护某个房间的在线观众列表与广播能力。
"""
from __future__ import annotations

import asyncio

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class RoomBroadcaster:
    """WebSocket 连接广播器。

    每个 ``LiveRoom`` 持有一个独立的 ``RoomBroadcaster`` 实例，
    负责管理该房间内的在线观众列表和消息广播。

    Attributes:
        active_connections: 当前在线的所有 WebSocket 连接。
    """

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """接受新连接并加入在线集合。"""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """从在线集合移除断开的连接。"""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: str) -> None:
        """向本房间所有在线观众广播消息。"""
        tasks = [ws.send_text(message) for ws in self.active_connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for ws, result in zip(self.active_connections.copy(), results):
            if isinstance(result, Exception):
                logger.warning("广播失败，移除断开的连接")
                self.active_connections.discard(ws)

    @property
    def online_count(self) -> int:
        """当前在线观众数。"""
        return len(self.active_connections)
