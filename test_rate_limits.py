import asyncio
import httpx
from websockets.asyncio.client import connect
import time

async def test_rest_rate_limit():
    print("="*50)
    print(" 验证 REST API 限流 (期望: 10/second) ")
    print("="*50)
    
    url = 'http://127.0.0.1:8000/api/rooms'
    print(f"请求 {url} 12 次...")
    
    async with httpx.AsyncClient() as client:
        responses = []
        for _ in range(12):
            try:
                resp = await client.get(url)
                responses.append(resp.status_code)
            except Exception as e:
                print(f"请求失败: {e}")
                
        print(f"状态码返回: {responses}")
        
        if 429 in responses:
            print("✅ 成功: 触发了 HTTP 429 Too Many Requests 限流！")
        else:
            print("❌ 失败: 没有触发 429 限流，或服务器未启动。")
            

async def test_ws_rate_limit():
    print("\n" + "="*50)
    print(" 验证 WebSocket 弹幕限流 (期望: 每 2 秒 1 次)")
    print("="*50)
    
    uri = 'ws://127.0.0.1:8000/ws/rooms/test_room'
    
    try:
        async with connect(uri) as websocket:
            print("✅已连接。现在快速发送两条弹幕...")
            
            # 第一条应该被允许
            await websocket.send('大家好，这是第一条测试弹幕')
            print(" -> 发送弹幕 1")
            
            # 极短时间内发送第二条（预期被拦截）
            time.sleep(0.1)
            await websocket.send('我是刷屏机器人！')
            print(" -> 发送弹幕 2 (过快)")
            
            # 读取服务端返回，检查是否有系统警告
            print("\n正在等待服务器响应...")
            warning_received = False
            for i in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"   服务器返回: {response}")
                    
                    if '[SYSTEM' in response:
                        warning_received = True
                        print("\n✅ 成功: 收到了服务端弹幕发送过快的限流警告！")
                        break
                except asyncio.TimeoutError:
                    pass
            
            if not warning_received:
                print("\n❌ 失败: 未收到系统限流警告。")
                
    except Exception as e:
        print(f"WebSocket 遇到了错误，请确认服务已启动: {e}")

async def main():
    print("🟢 开始执行限流防刷验证...\n")
    print("要求: 在运行本脚本前，请确保主程序服务已经在 http://127.0.0.1:8000 运行。\n")
    
    await test_rest_rate_limit()
    await test_ws_rate_limit()
    
    print("\n🏁 验证结束。")

if __name__ == '__main__':
    asyncio.run(main())
