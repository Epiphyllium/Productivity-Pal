import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from oscopilot import BaseModule
from oscopilot.prompts.taskplan_pt import taskPlannerPrompt
from oscopilot.utils.database import DailyLogDatabase
from oscopilot.modules.habit_tracker.habit_tracker import HabitTracker
from oscopilot.utils.utils import send_chat_prompts
import re
from add_events import AppleScript

load_dotenv(override=True)
# MODEL_NAME = os.getenv('CALENDAR_PLAN_ENDPOINT')

class TaskPlanner(BaseModule):
    def __init__(self):
        super().__init__()
        self.habit_tracker = HabitTracker()
        self.prompt = taskPlannerPrompt["planning_prompt"]
        self.appleScript=AppleScript()

    # 返回一个字典，key是任务名称，value是预计任务耗时
    # 举例 {'Financial Fraud Presentation - Research': '10 hours', 'Financial Fraud Presentation - Outline Creation': '3 hours'}
    def divide_task(self,task_name,description,deadline):
        try:
            sys_prompt = self.prompt['_SYSTEM_TASK_DECOMPOSE_PROMPT']
            user_prompt = self.prompt['_USER_TASK_DECOMPOSE_PROMPT'].format(
                task=task_name,
                description=description,
                deadline=deadline
            )
            response = send_chat_prompts(sys_prompt, user_prompt, self.llm)
            task_list = json.loads(response)
            # task_duration_dict = {item['Task']: item['Duration'] for item in task_list}
            task_duration_dict = {item['Task']: "" for item in task_list}
            return task_duration_dict
        except Exception as e:
            print(f"Error creating schedule: {e}")
            return None
    
    def schedule_task(self,user_id,task_dict,schedule_time,deadline):
        try:
            # Step1: 获取日历中deadline前存在的事件
            events=self.appleScript.get_calendar_events(deadline)
            
            # Step2: 获取用户最近7天的习惯
            # 返回一个json字段，Habits: 一个包含 Pattern 和 Description 的列表，说明用户的具体习惯和对应描述；Behavioral Tendencies: 一个包含 Observation 和 Details 的列表，描述用户行为模式的观察和细节
            habits={}
            for key in task_dict:
                habits[key]= self.habit_tracker.get_habit_about_certain_task(user_id, task=key, top_k=5)

            # Step3: 构建提示内容
            sys_prompt = self.prompt['_SYSTEM_TASK_SCHEDULE_PROMPT']
            user_prompt = self.prompt['_USER_TASK_SCHEDULE_PROMPT'].format(
                habits=habits,
                tasks=task_dict,
                existed_events=events,
                start_time=schedule_time,
                deadline=deadline
            )

            response= send_chat_prompts(sys_prompt, user_prompt, self.llm)
            print(response)
            schedule=json.loads(response.strip())
            return schedule
        except Exception as e:
            print(f"Error creating schedule: {e}")
            return None
        
    def execute_schedule_with_applescript(self,schedule):
        """
        根据生成的计划，使用 AppleScript 创建日历事件和提醒。
        """
        try:
            # 遍历计划中的任务
            for task in schedule:
                title = task["Task"]
                date = task["Date"]
                start_time = task["StartTime"]
                end_time = task["EndTime"]
                print(title,date,start_time,end_time)
                # 创建提醒和事件的 AppleScript
                self.appleScript.add_event(title, date, start_time,end_time)

        except Exception as e:
            print(f"执行计划时出错: {e}")


if __name__ == '__main__':
    task_planner = TaskPlanner()
    task_name = "Financial Fraud Presentation"
    task_description = "Prepare a presentation on financial fraud for the upcoming conference."
    tasks= task_planner.divide_task(task_name,task_description,"2024-11-30 23:59:59")  
    print("拆解的任务:\n",tasks)