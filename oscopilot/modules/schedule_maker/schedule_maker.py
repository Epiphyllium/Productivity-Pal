import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from oscopilot import BaseModule
from oscopilot.prompts.schedule_prompt import schedule_prompt
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
        datalog_db = DailyLogDatabase("daily_logs")
        logs = datalog_db.find_by_deadline(deadline_str)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        filtered_logs = [
            log for log in logs
            if "Date" in log and start_date.strftime("%Y%m%d") <= log["Date"] <= end_date.strftime("%Y%m%d")
        ]
        return filtered_logs[:limit] if limit > 0 else filtered_logs


    def fetch_habits(self,task):
        try:
            return self.habit_tracker.get_habit_about_certain_task(user_id=1, task=task, top_k=5)
        except Exception as e:
            print(f"Error fetching habits: {e}")
            return []

    def create_schedule(self, deadline, deadline_name):
        try:
            habits = self.fetch_habits(deadline_name)
            logs = self.fetch_logs_by_deadline(deadline)
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