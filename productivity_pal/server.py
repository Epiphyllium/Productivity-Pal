import asyncio 
import websockets
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from oscopilot.agents.task_schedule_agent import TaskScheduleAgent

agent=TaskScheduleAgent()

async def handle_websocket(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["dueDate"]!="":
                dueDate=data['dueDate']+" 23:59:59"
                print(dueDate)
                agent.schedule_task(3, data['name'], data['description'], dueDate)
            elif data["reDate"]!="":
                reDate=data["reDate"]+" 23:59:59"
                agent.set_reschedule_time(user_id=3,reschedule_time=reDate)
                agent.reschedule_task()
            print("Task Received:")
            print(f"Task Name: {data['name']}")
            print(f"Task Description: {data['description']}")
            print(f"Deadline: {data['dueDate']}")
            print(f"Reminder Time: {data['reDate']}")
            # 发送确认消息给客户端
            await websocket.send(json.dumps({"status": "success"}))
    except Exception as e:
        print(f"处理消息时出错: {e}")

async def main():
    print("WebSocket server is running, waiting for connection...")
    async with websockets.serve(handle_websocket, "localhost", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWebSocket server stopped.")