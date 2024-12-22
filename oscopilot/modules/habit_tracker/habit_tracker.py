import os
from dotenv import load_dotenv

from oscopilot import BaseModule
from oscopilot.prompts.habit_prompt import habit_prompt
from oscopilot.utils.database import DailyLogDatabase
from oscopilot.utils.utils import send_chat_prompts

load_dotenv(override=True)
MODEL_NAME = os.getenv('HABIT_EXTRACTION_ENDPOINT')


class HabitTracker(BaseModule):
    def __init__(self):
        super().__init__()
        self.daily_log_db = DailyLogDatabase("DailyLogs")


    # def save_habit(self, habit):
    #     data = json.loads(habit)
    #     for key, value in data.items():
    #         habit_db = HabitDatabase(key)
    #         habit_db.insert(value)
    #     return "Habit saved successfully"

    def get_habit_about_certain_task(self, user_id,  task, top_k):
        """
        Get the habit about a certain task.
        1. From daily log database, get the logs of the task via embedding.
        2. Use the habit extraction model to extract the habit.
        3. Return the habit.

        :param user_id: user id
        :param task: task name and description
        :param top_k: top k logs

        :return: habit
        """
        logs = self.daily_log_db.find_relevant_datalogs(user_id=user_id, task=task, top_k=top_k,need_to_prompt=True)
        # self.llm.set_model_name(MODEL_NAME)
        if len(logs) == 0:
            return "No logs found"
        user_prompt = habit_prompt["USER_PROMPT"] + "\n " + "**Activities**: \n" + self.transfer_data_to_prompt(logs)
        response = send_chat_prompts(habit_prompt["USER_PROMPT"], user_prompt, self.llm, prefix="Overall")
        normalized_habits = self.extract_habit_from_response(response)
        return normalized_habits

if __name__ == '__main__':
    habit_tracker = HabitTracker()
    logs = habit_tracker.get_habit_about_certain_task(user_id=1, task="coding", top_k=20)
    print(logs)
