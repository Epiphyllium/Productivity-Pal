import asyncio 
import websockets
import json

async def handle_websocket(websocket):  # 添加 path 参数
    try:
        async for message in websocket:
            data = json.loads(message)
            print("收到任务数据:")
            print(f"任务名: {data['name']}")
            print(f"任务描述: {data['description']}")
            print(f"截止日期: {data['dueDate']}")
            
            # 发送确认消息给客户端
            await websocket.send(json.dumps({"status": "success"}))
    except Exception as e:
        print(f"处理消息时出错: {e}")

async def main():
    print("WebSocket 服务器已启动，等待连接...")
    async with websockets.serve(handle_websocket, "localhost", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")