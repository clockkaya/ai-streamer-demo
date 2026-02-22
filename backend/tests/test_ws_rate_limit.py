import asyncio
import time
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from fastapi import WebSocket

from app.api.live_stream_ws import websocket_room_endpoint
from app.core.rate_limit import WebSocketRateLimiter
from app.core.settings import settings
from app.main import app


# ==============================================================================
# 单元测试: 测试 WebSocketRateLimiter 逻辑
# ==============================================================================
def test_websocket_rate_limiter_unit():
    """测试 WebSocket 内存限流器的基础逻辑"""
    limiter = WebSocketRateLimiter(interval_seconds=0.5)
    client_id = 999
    
    # 第一次发消息应该允许
    assert limiter.is_allowed(client_id) is True
    
    # 立刻发第二次应该被拦截
    assert limiter.is_allowed(client_id) is False
    
    # 等待超过间隔时间后应该放行
    time.sleep(0.6)
    assert limiter.is_allowed(client_id) is True
    
    # 最后清理记录
    limiter.remove_client(client_id)
    assert client_id not in limiter._last_message_time


# ==============================================================================
# 集成测试: 测试 WebSocket 端点的限流防刷机制
# ==============================================================================
@pytest.mark.asyncio
async def test_websocket_endpoint_rate_limit(mock_gemini_client):
    """测试 WebSocket 端点在极速发弹幕情况下的拦截机制。"""
    original_interval = settings.WS_RATE_LIMIT_INTERVAL
    settings.WS_RATE_LIMIT_INTERVAL = 0.5
    
    
    original_interval = settings.WS_RATE_LIMIT_INTERVAL
    settings.WS_RATE_LIMIT_INTERVAL = 0.5
    
    try:
        # 使用 mock WebSocket 进行测试，避开 TestClient 的 httpx 兼容性问题
        mock_ws = AsyncMock(spec=WebSocket)
        
        # 准备两次快速接收的消息序列
        # 第一次返回消息 1，第二次返回消息 2，第三次抛出断开连接异常结束此循环
        mock_ws.receive_text.side_effect = ["Hello 1", "Hello 2", asyncio.CancelledError()]
        
        # 覆写依赖，使得 TTS 和 MongoDB 不作处理避免调用外部API
        with patch('app.api.live_stream_ws.generate_audio_base64', new_callable=AsyncMock) as mock_tts, \
             patch('app.api.live_stream_ws.get_live_system') as mock_sys:
            
            mock_tts.return_value = "" # TTS 模拟返回为空
            
            # mock get_live_system 返回假房间
            from unittest.mock import MagicMock
            mock_room = MagicMock()
            mock_room.online_count = 1
            mock_room.broadcaster.connect = AsyncMock()
            mock_room.broadcaster.disconnect = AsyncMock()
            mock_room.broadcaster.broadcast = AsyncMock()
            mock_system = MagicMock()
            mock_system.get_room = AsyncMock(return_value=mock_room)
            mock_sys.return_value = mock_system
            
            try:
                await websocket_room_endpoint(websocket=mock_ws, room_id="test_rate_room")
            except asyncio.CancelledError:
                pass  # 预期异常，用于中止消息循环
                
            # 检查 websocket.send_text 是否曾发出过限流警告
            warning_called = False
            for call in mock_ws.send_text.call_args_list:
                args, kwargs = call
                if args and "[SYSTEM:您发送弹幕的速度太快啦" in args[0]:
                    warning_called = True
                    break
                    
            assert warning_called, "并没有捕捉到触发限流后的系统提示（send_text 未被警告内容调用）"
                
    finally:
        # 还原配置
        settings.WS_RATE_LIMIT_INTERVAL = original_interval

