from oscopilot.modules.planner.task_planner import TaskPlanner
from oscopilot.modules.schedule_maker.rescheduler import Rescheduler
import datetime
from oscopilot.utils.database import DailyLogDatabase, DeadlineDatabase



class TaskScheduleAgent:
    def __init__(self):
        self.task_planner = TaskPlanner()
        self.deadline_db = DeadlineDatabase("Deadlines")
     

    def set_reschedule_time(self, reschedule_time):
        self.rescheduler = Rescheduler(user_id=1, reschedule_time=reschedule_time)

    def schedule_task(self, user_id, task_name,description,deadline):
        deadline=int(datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S").timestamp())
        # 大任务存入数据库
        original_task={"Title": task_name, "Description": description, "Deadline": deadline}
        #  mark
        id=self.deadline_db.insert_one_task(original_task,user_id,task_type=0,times_format="")
        if id == None:
            return 
        # 拿任务
        dic=self.deadline_db.find_by_id(id,user_id,need_to_prompt=True)
        task_name=dic["Title"]
        description=dic["Description"]
        # TODO 时间部分不匹配，差秒数
        deadline=dic["Deadline"]+":00"

        tasks_dict=self.task_planner.divide_task(task_name,description,deadline)
        print(tasks_dict)
        schedule_time=datetime.datetime.now()
        print(schedule_time)
        schedule=self.task_planner.schedule_task(user_id, tasks_dict, schedule_time, deadline)
        self.task_planner.execute_schedule_with_applescript(schedule)

        # 小任务存入数据库
        subtask_id_list=[]
        for task in schedule:
            add_task={}
            start_datetime_str = f'{task["Date"]} {task["StartTime"]}'
            end_datetime_str = f'{task["Date"]} {task["EndTime"]}'

            start_timestamp = int(datetime.datetime.strptime(start_datetime_str, "%Y-%m-%d %I:%M %p").timestamp())
            end_timestamp = int(datetime.datetime.strptime(end_datetime_str, "%Y-%m-%d %I:%M %p").timestamp())

            add_task["Title"]=task["Task"]
            add_task["Status"]=0
            add_task["Parent Task"]= [id]
            add_task["Start"]=start_timestamp
            add_task["Deadline"]=end_timestamp

            subtask_id=self.deadline_db.insert_one_task(add_task,user_id,1,times_format="")
            subtask_id_list.append(subtask_id)
        # 更新大任务
        self.deadline_db.update_subtasks(user_id,id,subtask_id_list,override=False)
        self.deadline_db.update_status(user_id,id,1)
        return 
    
    def reschedule_task(self,user_id, reschedule_time):
        tasks=self.rescheduler.get_tasks_to_reschedule()

if __name__=="__main__":
    agent=TaskScheduleAgent()
    task_name = "Financial Fraud Presentation"
    task_description = "Prepare a presentation on financial fraud for the upcoming conference." 
    agent.schedule_task(2,task_name,task_description,"2024-11-30 23:59:59")