import unittest
from datetime import datetime
from oscopilot.prompts.schedule_prompt import schedule_prompt
from pymongo import MongoClient
from oscopilot.modules.planner.task_planner import TaskPlanner
from oscopilot.utils.database import DeadlineDatabase
from oscopilot.modules.schedule_maker.rescheduler import Rescheduler

# 初始化参数
user_id = 1
reschedule_time = "2024-11-16 23:59"  # 当前时间作为重新调度的时间

def test_get_tasks_to_reschedule():
    rescheduler = Rescheduler(user_id, reschedule_time, schedule_prompt)

    try:
        tasks = rescheduler.get_tasks_to_reschedule()
        if tasks:
            print("[Debug] Tasks retrieved for rescheduling:")
            for task in tasks:
                title = task.get("Title", "No Title")
                description = task.get("Description", "No Description")
                duration = task.get("Estimated Duration", "Unknown Duration")
                print(f"- Title: {title}")
                print(f"  Description: {description}")
                print(f"  Estimated Duration: {duration}")
                print()
        else:
            print("No tasks found for rescheduling.")
    except Exception as e:
        print(f"Error occurred while retrieving tasks: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_tasks_to_reschedule()