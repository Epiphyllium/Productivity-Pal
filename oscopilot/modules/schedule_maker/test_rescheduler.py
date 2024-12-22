import json
import unittest
from datetime import datetime
from oscopilot.modules.schedule_maker.rescheduler import Rescheduler
from oscopilot.prompts.schedule_prompt import schedule_prompt
from oscopilot.modules.habit_tracker.habit_tracker import HabitTracker



class TestReschedulerWithRealData(unittest.TestCase):
    def setUp(self):
        """初始化测试数据"""
        self.user_id = 1
        reschedule_time = "2024-11-17 10:00"
        self.start_time = datetime.strptime("2024-11-17 00:00", "%Y-%m-%d %H:%M")
        self.deadline = datetime.strptime("2024-11-30 23:59", "%Y-%m-%d %H:%M")
        self.rescheduler = Rescheduler(self.user_id, reschedule_time, schedule_prompt)

        # 手动赋值任务列表
        self.tasks = [
            {
                "Title": "Christmas Holiday Planning",
                "Description": "Plan the Christmas holiday activities, including gift shopping, travel arrangements, and dinner preparation.",
                "Start Time": "1734688800",
                "Status": 1
            },
            {
                "Title": "Deep Learning Final Exam",
                "Description": "The final examination on deep learning, including basic information, CNN, GNN, and RNN.",
                "Start Time": "1734172200",
                "Status": 0
            },
        ]

    def test_execute_reschedule_with_real_data(self):
        """使用真实数据测试重新调度任务"""
        print("[Debug] Tasks for Rescheduling:")
        for task in self.tasks:
            print(f"Title: {task['Title']}, Description: {task['Description']}")

        # 调用真实的 reschedule_tasks 方法
        new_schedule = self.rescheduler.reschedule_tasks(self.tasks, self.start_time, self.deadline)

        # 验证新生成的计划是否正确
        self.assertIsInstance(new_schedule, list, "Reschedule result should be a list.")
        self.assertGreater(len(new_schedule), 0, "Generated schedule should not be empty.")

        for task in new_schedule:
            self.assertIsInstance(task, dict, "Each task in the schedule should be a dictionary.")
            self.assertIn("Task", task, "Each task should have a 'Task' key.")
            self.assertIn("Date", task, "Each task should have a 'Date' key.")
            self.assertIn("StartTime", task, "Each task should have a 'StartTime' key.")
            self.assertIn("EndTime", task, "Each task should have an 'EndTime' key.")

        # 输出调试信息
        print("[Debug] New schedule:", new_schedule)

if __name__ == "__main__":
    unittest.main()