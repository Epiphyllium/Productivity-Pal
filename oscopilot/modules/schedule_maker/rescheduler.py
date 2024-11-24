import json
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from oscopilot import BaseModule
from oscopilot.prompts.Schedule_Prompt import schedule_prompt
from oscopilot.utils.database import DailyLogDatabase, DeadlineDatabase
from oscopilot.modules.planner.task_planner import TaskPlanner
from oscopilot.utils.utils import send_chat_prompts
from string import Template

load_dotenv(override=True)

class Rescheduler(BaseModule):
    def __init__(self, user_id, reschedule_time):
        super().__init__()
        self.user_id = user_id
        self.reschedule_time = datetime.strptime(reschedule_time, "%Y-%m-%d %H:%M")
        self.daily_log_db = DailyLogDatabase("DailyLogs")
        self.deadline_db = DeadlineDatabase("Deadlines")

    def get_tasks_to_reschedule(self):
        """获取需要重新调度的任务"""
        try:
            reschedule_timestamp = int(self.reschedule_time.timestamp())
            tasks_need_reschedule = self.deadline_db.get_tasks_need_to_reschedule(user_id=self.user_id, reschedule_time=reschedule_timestamp,need_to_prompt=False)
            # 转换任务格式
            structured_tasks = []
            for task in tasks_need_reschedule:
                if "Start Time" in task and "Deadline" in task:
                    start_time = task["Start Time"]
                    deadline = task["Deadline"]
                    duration_hours = (deadline - start_time).total_seconds() / 3600
                    structured_tasks.append({
                        "Title": task.get("Title", "Unnamed Task"),
                        "Description": task.get("Description", "No Description"),
                        "Estimated Duration": f"{duration_hours:.2f} hours"
                    })
            return structured_tasks
        except Exception as e:
            print(f"Error retrieving tasks for rescheduling: {e}")
            return []

    def reschedule_tasks(self, tasks, start_time, deadline):
        """生成新任务计划"""
        try:
            # Step 1: 获取每个任务的相关习惯并生成对应的 prompt
            all_habits_prompts = []  # 用于存储每个任务的习惯
            task_prompts = []  # 用于存储每个任务的信息

            for task in tasks:
                task_title = task.get("Title", "Unnamed Task")
                task_description = task.get("Description", "No Description")

                # 添加任务信息到任务 prompt 中
                task_prompts.append({
                    "Title": task_title,
                    "Description": task_description,
                    "Start Time": task.get("Start Time", "No Start Time"),
                    "Status": task.get("Status", "Unknown")
                })

                # 调用 get_habit_from_logs 获取任务相关的 habits
                task_habits = self.habit_tracker.get_habit_about_certain_task(
                    user_id=self.user_id,
                    top_k=20,  # 返回最多20个相关日志
                    task=f"{task_title} {task_description}"
                )
                print(f"[Debug] Retrieved habits for task '{task_title}':\n", json.dumps(task_habits, indent=2, ensure_ascii=False))

                # 确保 task_habits 不为空，并追踪其值
                if not task_habits:
                    task_habits = [
                        {"Pattern": "No habits found", "Description": "No habits could be extracted for this task."}]
                else:
                          json.dumps(task_habits, indent=2, ensure_ascii=False)

                # 检查 task_habits 数据类型
                if isinstance(task_habits, str):
                    try:
                        # 解析字符串为 JSON
                        task_habits = json.loads(task_habits)
                        print("[Debug] Parsed task_habits as JSON:\n",
                              json.dumps(task_habits, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError as e:
                        print("[Error] task_habits is not valid JSON:", e)
                        task_habits = [{"Pattern": "Parsing Error", "Description": str(e)}]

                # 确保 task_habits 不为空，并追踪其值
                if not task_habits:
                    print(f"[Warning] task_habits is empty for task '{task_title}'. Using default value.")
                    task_habits = [
                        {"Pattern": "No habits found", "Description": "No habits could be extracted for this task."}]
                else:
                    print(f"[Debug] Non-empty task_habits for task '{task_title}':\n",
                          json.dumps(task_habits, indent=2, ensure_ascii=False))

                # 检查 task_habits 数据类型
                if isinstance(task_habits, dict):
                    task_habits = [
                        {"Pattern": task_habits.get("Pattern", ""), "Description": task_habits.get("Description", "")}
                    ]
                elif isinstance(task_habits, list):
                    # 确保每一项都有必要的字段
                    processed_habits = []
                    for habit in task_habits:
                        if isinstance(habit, dict):
                            pattern = habit.get("Pattern", None)
                            description = habit.get("Description", None)
                            if pattern and description:
                                processed_habits.append({"Pattern": pattern, "Description": description})
                            else:
                                print(f"[Warning] Skipping incomplete habit: {habit}")
                    task_habits = processed_habits

                    task_habits = [
                        {"Pattern": "No habits found", "Description": "No habits could be extracted for this task."}]

                # 拼接到 all_habits_prompts
                all_habits_prompts.append({
                    "Task": task_title,
                    "Habits": task_habits
                })
                print(f"[Debug] Added habits for task '{task_title}':\n",
                      json.dumps(task_habits, indent=2, ensure_ascii=False))

            # Step 2: 构建完整的 Habits 和 Tasks prompt
            print("[Debug] All habits prompts:\n", json.dumps(all_habits_prompts, indent=2, ensure_ascii=False))
            print("[Debug] Task prompts:\n", json.dumps(task_prompts, indent=2, ensure_ascii=False))

            habits_str = json.dumps(all_habits_prompts, indent=2, ensure_ascii=False)
            tasks_str = json.dumps(task_prompts, indent=2, ensure_ascii=False)
            print("[Debug] Habits JSON before substitution:\n", habits_str)
            print("[Debug] Tasks JSON before substitution:\n", tasks_str)
            user_prompt_template = Template(self.prompt['USER_PROMPT'])
            user_prompt = user_prompt_template.safe_substitute({
                "Habits": habits_str,
                "Tasks": tasks_str
            })
            print("[Debug] Finalized USER_PROMPT:\n", user_prompt)
            sys_prompt = self.prompt['SYSTEM_PROMPT']

            # 调用大模型生成新计划
            response = send_chat_prompts(sys_prompt, user_prompt, self.llm, prefix="Reschedule")
            normalized_plans = self.clean_and_parse_json(response)
            print("[Info] Chat Response:\n", normalized_plans)
            # 提取 JSON 数据
            try:
                if isinstance(normalized_plans, (list, dict)):
                    print("[Debug] normalized_plans is already a Python object.")
                    return normalized_plans
                schedule = json.loads(normalized_plans)  # response 是一个 JSON 字符串
                if isinstance(schedule, list):
                    print("[Debug] Successfully parsed schedule as JSON list.")
                    return normalized_plans
            except json.JSONDecodeError as e:
                print(f"[Error] JSON decode error: {e}")
                print("[Debug] Raw response causing error:\n", normalized_plans)
                return None

            print("[Error] Response is not a valid JSON list.")
            return None
        except Exception as e:
            print(f"[Error] Unexpected error during rescheduling: {e}")
            return None

    def execute_reschedule(self, start_time, deadline):
        """执行重新调度任务"""
        try:
            tasks_to_reschedule = self.deadline_db.get_tasks_need_to_reschedule(user_id=self.user_id, reschedule_time=self.reschedule_time.timestamp())
            if not tasks_to_reschedule:
                print("[Info] No tasks to reschedule.")
                return None

            # 输出待处理任务的调试信息
            print("[Debug] Tasks to reschedule:", tasks_to_reschedule)

            # 调用 reschedule_tasks 函数生成新的计划
            new_schedule = self.reschedule_tasks(tasks_to_reschedule, start_time, deadline)

            # 输出新的调度计划
            print("[Debug] New schedule:", new_schedule)

            return new_schedule
        except Exception as e:
            print(f"[Error] Rescheduling failed: {e}")
            return None



if __name__ == "__main__":
    user_id = 1
    reschedule_time = "2023-11-17 10:00"
    start_time = datetime.strptime("2023-11-17 00:00", "%Y-%m-%d %H:%M")
    deadline = datetime.strptime("2023-11-20 23:59", "%Y-%m-%d %H:%M")
    rescheduler = Rescheduler(user_id, reschedule_time, schedule_prompt)
    new_schedule = rescheduler.execute_reschedule(start_time, deadline)
    print("重新调度的任务计划：", json.dumps(new_schedule, indent=2, ensure_ascii=False))