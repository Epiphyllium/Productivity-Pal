import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from oscopilot import BaseModule
from oscopilot.prompts.Schedule_Prompt import schedule_prompt
from oscopilot.utils.database import DailyLogDatabase
from oscopilot.modules.habit_tracker.habit_tracker import HabitTracker
from oscopilot.utils.utils import send_chat_prompts

load_dotenv(override=True)
MODEL_NAME = os.getenv('CALENDAR_PLAN_ENDPOINT')

class ScheduleMaker(BaseModule):
    def __init__(self):
        super().__init__()
        self.habit_tracker = HabitTracker()

    def fetch_logs_by_deadline(self, deadline_str, days=7, limit=-1):
        """
        根据给定的截止日期查找与时段相似的日志数据。
        """
        datalog_db = DailyLogDatabase("daily_logs")
        logs = datalog_db.find_by_deadline(deadline_str)
        # 过滤最近 7 天内的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        filtered_logs = [
            log for log in logs
            if "Date" in log and start_date.strftime("%Y%m%d") <= log["Date"] <= end_date.strftime("%Y%m%d")
        ]
        return filtered_logs[:limit] if limit > 0 else filtered_logs


    def fetch_habits(self,task):
        """
        调用 HabitTracker 获取最近 7 天的习惯。
        """
        try:
            return self.habit_tracker.get_habit_from_logs(days=7, limit=15, task=task)
        except Exception as e:
            print(f"Error fetching habits: {e}")
            return []

    def create_schedule(self, deadline, deadline_name):
        try:
            # Step 1: 获取 Habit 数据
            habits = self.fetch_habits(deadline_name)

            # Step 2: 根据 Deadline 获取日志
            logs = self.fetch_logs_by_deadline(deadline)

            # Step 3: 构建提示内容
            user_prompt = (
                schedule_prompt["USER_PROMPT"]
                + f"\n**Deadline Name:** {deadline_name}"
                + "\n**Deadline:** "
                + deadline
                + "\n**Logs:** "
                + json.dumps(logs, indent=2)
                + "\n**Habits:** "
                + json.dumps(habits, indent=2)
            )

            # Step 4: 调用模型生成计划
            self.llm.set_model_name(MODEL_NAME)
            response = send_chat_prompts(schedule_prompt["USER_PROMPT"], user_prompt, self.llm, prefix="Schedule")
            return response
        except Exception as e:
            print(f"Error creating schedule: {e}")
            return None



if __name__ == '__main__':
    schedule_maker = ScheduleMaker()
    deadline = "202411201200"  # 示例 Deadline
    deadline_name = "Financial Fraud Presentation"
    schedule = schedule_maker.create_schedule(deadline, deadline_name)
    print("生成的计划表:\n", schedule)