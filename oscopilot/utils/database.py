import uuid
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from datetime import datetime,timedelta

load_dotenv(override=True)
MODEL_NAME = os.getenv('MODEL_NAME')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')
BASE_URL = os.getenv('OPENAI_BASE_URL')
CONNECTION_STRING = os.getenv('CONNECTION_STRING')

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(CONNECTION_STRING)
            self.db = self.client['productivity_pal']
            self.model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
            Database.model_loaded = True
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            raise

    def get_embedding(self, data):
        """Generates vector embeddings for the given data."""
        try:
            embedding = self.model.encode(data)
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise
        return embedding.tolist()

    def get_collection(self, collection_name):
        """Helper method to fetch a collection from the database."""
        try:
            return self.db[collection_name]
        except Exception as e:
            print.error(f"Error fetching collection {collection_name}: {e}")
            raise

    def timestamp_to_date(self, timestamp, output_date_format):
        date_obj = datetime.fromtimestamp(timestamp)
        return date_obj.strftime(output_date_format)

    def date_to_timestamp(self, date_str, input_date_format):
        date_obj = datetime.strptime(date_str, input_date_format)
        return int(date_obj.timestamp())

class DailyLogDatabase(Database):
    def __init__(self, collection_name):
        super().__init__()
        self.collection = self.db[collection_name]


    def insert_one_log(self, log, user_id, time_format = "", date_format =""):
        """
        Inserts a single log into the database.
        log (dict): The log details to be inserted.
        A full input log object should contain the following fields:
        log :{
            "Active": "Activity",
            "Type": "Type",
            "Start Time": "Start Time", # optional, format = "%Y%m%d%H%M", e.g., "202411201200"
            "End Time": "End Time", # optional, format = "%Y%m%d%H%M", e.g., "202411201200"
            "Date": "Date"
        }
        time_format (str): The format of the time fields. e.g., "%Y%m%d%H%M"
            default is "", which means timestamp
        date_format (str): The format of the date field. e.g., "%Y%m%d"
            default is "", which means timestamp
        user_id (int): The user ID associated with the log. Default is 1.
        """
        if "Active" not in log:
            log["Active"] = ""
        if "Type" not in log:
            log["Type"] = ""
        if "Start Time" not in log:
            log["Start Time"] = ""
        if "End Time" not in log:
            log["End Time"] = ""
        if "Date" not in log:
            log["Date"] = ""
        text = "Active: "+ log["Active"] + "; " +"Type: "+ log["Type"] + "; "
        if time_format != "" and log["Start Time"] != "":
            log["Start Time"] = self.date_to_timestamp(log["Start Time"], time_format)
        if time_format != "" and log["End Time"] != "":
            log["End Time"] = self.date_to_timestamp(log["End Time"], time_format)
        if date_format != "" and log["Date"] != "":
            log["Date"] = self.date_to_timestamp(log["Date"], date_format)
        if log["Start Time"] != "" and log["End Time"] != "":
            log["Duration"] = log["End Time"] - log["Start Time"]
        log["user_id"] = user_id
        embedding = self.get_embedding(text)
        document = {**log, "text": text, "embedding": embedding}
        try:
            result = self.collection.insert_one(document)
            return result.inserted_id
        except Exception as e:
            print(f"Error inserting document: {e}")
            return None

    def _find(self, pipeline, need_to_prompt=False):
        """
        private method to find logs based on the pipeline.
        """
        cursors = self.collection.aggregate(pipeline)
        response = []
        for cursor in cursors:
            response.append(cursor)
        if need_to_prompt:
            logs = []
            for item in response:
                log = {}
                log["Active"] = item["Active"]
                log["Type"] = item["Type"]
                if "Date" in item and item["Date"] != "":
                    log["Date"] = self.timestamp_to_date(item["Date"], "%Y-%m-%d") # Date: 2024-09-27;
                else:
                    log["Date"] = ""
                if "Start Time" in item and item["Start Time"] != "":
                    log["Start Time"] = self.timestamp_to_date(item["Start Time"], "%Y-%m-%d %H:%M") # Start Time: 2024-09-27 16:01;
                else:
                    log["Start Time"] = ""
                if "End Time" in item and item["End Time"] != "":
                    log["End Time"] = self.timestamp_to_date(item["End Time"], "%Y-%m-%d %H:%M")
                else:
                    log["End Time"] = ""
                if "Duration" in item and item["Duration"] != "":
                    hours = item["Duration"] // 3600
                    minutes = (item["Duration"] % 3600) // 60
                    if hours > 0:
                        log["Duration"] = f"{hours}h {minutes}min"
                    else:
                        log["Duration"] = f"{minutes} minutes"
                else:
                    log["Duration"] = ""
                logs.append(log)
            return logs
        else:
            return response


    def find_relevant_datalogs(self, user_id, top_k, task: str, need_to_prompt=False):
        """
        Finds relevant logs based on the user_id and task.
        user_id (int): The user ID associated with the logs.
        top_k (int): The number of logs to return.
        task (str): The task to match. It's Deadline's title + Description
        need_to_prompt (bool): A flag indicating whether the found logs should be prompted to the user.
            if True, the timestamp fields will be converted to human-readable date-time strings.
        """
        pipeline = [
            {
                "$search": {
                    "knnBeta": {
                        "vector": self.get_embedding(task),  # Generate embedding for the task
                        "path": "embedding",
                        "k": top_k  # Retrieve top_k most relevant results
                    }
                }
            },
            {
                "$match": {
                    "user_id": user_id  # Filter results by user_id
                }
            },
            {
                "$sort": {
                    "similarity": -1  # Sort results by similarity in descending order
                }
            },
            {
                "$project": {
                    "user_id": 0,
                    "text": 0,
                    "embedding": 0
                }
            }
        ]
        logs = self._find(pipeline,need_to_prompt)
        return logs


    #
    # def fetch_recent_logs(self, user_id, top_k, days = -1, task=None):
    #     dailylog_db = DailyLogDatabase("DailyLogs")
    #     dailylog_db.collection.create_index([("Date", DESCENDING)])
    #     dailylog_db.collection.create_index(["user_id"])
    #     indexes = dailylog_db.collection.index_information()
    #     # print(indexes)
    #     query = {
    #         "user_id": user_id
    #     }
    #     if days > 0:
    #         end_date = datetime.now()
    #         start_date = end_date - timedelta(days=days)
    #         start_timestamp = int(start_date.timestamp())
    #         end_timestamp = int(end_date.timestamp())
    #         print(start_timestamp, end_timestamp)
    #         query["Date"] = {"$gte": start_timestamp, "$lte": end_timestamp},
    #     pipeline = []
    #     if task is not None:
    #         task_embedding = dailylog_db.get_embedding(task)
    #         pipeline.append({
    #             "$search": {
    #                 "knnBeta": {
    #                     "vector": task_embedding,
    #                     "path": "embedding",
    #                     "k": top_k
    #                 }
    #             }
    #         })
    #     pipeline.append({"$match": query})
    #     pipeline.append({"$limit": top_k})
    #     logs = dailylog_db._find(pipeline)
    #     print(f"Find {len(logs)} logs")
    #     return logs





# class HabitDatabase(Database):
#     def __init__(self, collection_name):
#         super().__init__()
#         self.collection = self.db[collection_name]
#     def insert(self, data, user_id):
#         i = 0
#         insert_count = 0
#         for item in data:
#             i = i+1
#             for key, value in item.items():
#                 text = key + ": " + str(value)
#             embedding = self.get_embedding(text)
#             document = {**item, "user_id":user_id, "text": text, "embedding": embedding}
#             try:
#                 self.collection.insert_one(document)
#                 insert_count = insert_count + 1
#             except Exception as e:
#                 print(f"Error inserting document {i}: {e}")
#                 continue
#         print(f"Inserted {insert_count} documents into the collection.")
#
#     def find_by_deadline(self, deadline_str):
#         """
#         Finds documents with a deadline matching or earlier than the specified deadline.
#
#         Parameters:
#         deadline (str): The deadline date in ISO 8601 format (e.g., "2024-11-30").
#
#         Returns:
#         list: A list of matching documents.
#         """
#         try:
#             # 将截止日期字符串转换为 datetime 对象
#             deadline = datetime.strptime(deadline_str, "%Y%m%d%H%M")
#             now = datetime.now()
#
#             # 计算从当前时间到截止日期的持续时长（分钟）
#             duration = (deadline - now).total_seconds() / 60
#
#             # 使用 MongoDB 聚合查询最大值和最小值
#             aggregation_pipeline = [
#                 {
#                     "$addFields": {
#                         "Duration": {
#                             "$cond": [
#                                 {"$and": [{"$ifNull": ["$Start Time", False]}, {"$ifNull": ["$End Time", False]}]},
#                                 {
#                                     "$divide": [
#                                         {"$subtract": [
#                                             {"$dateFromString": {"dateString": "$End Time", "format": "%Y%m%d%H%M"}},
#                                             {"$dateFromString": {"dateString": "$Start Time", "format": "%Y%m%d%H%M"}}
#                                         ]},
#                                         60 * 1000  # 转换为分钟
#                                     ]
#                                 },
#                                 None
#                             ]
#                         }
#                     }
#                 },
#                 {"$match": {"Duration": {"$ne": None}}},  # 排除没有持续时间的记录
#                 {
#                     "$group": {
#                         "_id": None,
#                         "max_duration": {"$max": "$Duration"},
#                         "min_duration": {"$min": "$Duration"},
#                     }
#                 }
#             ]
#
#             duration_stats = list(self.collection.aggregate(aggregation_pipeline))
#             if not duration_stats:
#                 print("数据库中没有有效的持续时长记录。")
#                 return []
#
#             max_duration = duration_stats[0]["max_duration"]
#             min_duration = duration_stats[0]["min_duration"]
#
#             # 动态调整误差范围
#             if duration < min_duration:
#                 tolerance = max(10, min_duration * 0.1)
#             elif duration > max_duration:
#                 tolerance = max(10, max_duration * 0.1)
#             else:
#                 tolerance = max(10, duration * 0.2)
#
#             # 匹配持续时长与用户输入接近的记录
#             results = []
#             logs = self.collection.find()
#             for log in logs:
#                 if "Start Time" in log and "End Time" in log:
#                     try:
#                         start_time = datetime.strptime(log["Start Time"], "%Y%m%d%H%M")
#                         end_time = datetime.strptime(log["End Time"], "%Y%m%d%H%M")
#                         log_duration = (end_time - start_time).total_seconds() / 60
#
#                         # 打印调试信息
#                         print(
#                             f"记录 {log['Name']} 的时长: {log_duration:.2f} 分钟, 目标时长: {duration:.2f} 分钟, 容差范围: ±{tolerance:.2f} 分钟")
#
#                         # 判断持续时长是否在容许误差范围内
#                         if abs(log_duration - duration) <= tolerance:
#                             results.append(log)
#                     except Exception as e:
#                         print(f"Error processing log: {log}, Error: {e}")
#                 else:
#                     print(f"跳过无效记录: {log}")
#
#             return results
#
#         except Exception as e:
#             print(f"Error during find_by_deadline: {e}")
#             return []

class DeadlineDatabase(Database):
    def __init__(self,collection_name):
        super().__init__()
        self.collection = self.db[collection_name]
    # ----------------------------- insert --------------------------------
    def insert_one_task(self, task, user_id, task_type,times_format=""):
        """
        Inserts a single task into the database.
        task (dict): The task details to be inserted.
        A full input task object should contain the following fields:
        Task :{
            "Title": "Task Title", # required
            "Description": "Task Description", # optional
            "Start Time": "Task Start Time", # optional, format = "%Y%m%d%H%M", e.g., "202411201200"
            "Deadline": "Task Deadline", #required
            "Subtasks": [], # if task is a parent task, this field will contain subtasks' id, optional
            "Parent Task": [], # if task is a subtask, this field will contain parent task's id, required for subtasks
            "Status": 0, # optional
                for subtasks: default is 0. 0 - Incomplete, 1 - ongoing, 2 - completed, -1 - overdue
                for parent tasks: default is 0. 0 - Not start yet, 10 - allocated, 20 - completed , -10 overdue
        }
        times_format (str): The format of the time fields. e.g., "%Y%m%d%H%M"
            default is "", which means timestamp
        user_id (int): The user ID associated with the task. Default is 1.
        task_type (int): The type of task to be inserted. 0 for Task, 1 for Subtask.
        """
        if "Parent Task" not in task:
            task["Parent Task"] = []
        if "Subtasks" not in task:
            task["Subtasks"] = []
        if "Start Time" not in task:
            task["Start Time"] = ""
        if "Description" not in task:
            task["Description"] = ""
        if "Status" not in task:
            task["Status"] = 0
        if "Deadline" not in task or "Title" not in task or task["Deadline"]=="" or task["Title"]=="":
            raise ValueError("Task must contain a title and deadline.")

        text = "Title: "+ task["Title"] + "; " +"Description: "+ task["Description"] + "; "
        if times_format != "":
            task["Deadline"] = self.date_to_timestamp(task["Deadline"], times_format)
        if task["Start Time"]!="" and times_format != "":
            task["Start Time"] = self.date_to_timestamp(task["Start Time"], times_format)
        task["Type"] = task_type # 0 - Task, 1 - Subtask
        task["user_id"] = user_id
        embedding = self.get_embedding(text)
        document = {**task, "text": text, "embedding": embedding}
        try:
            result = self.collection.insert_one(document)
            return result.inserted_id
        except Exception as e:
            print(f"Error inserting document: {e}")
            return None

    # ----------------------------- find --------------------------------
    def find_by_id(self, document_id, user_id, need_to_prompt=False):
        """
        Finds a task or subtask by its document_id.
        document_id (str): The id of the task or subtask to find.
        need_to_prompt (bool): A flag indicating whether the found task should be prompted to the user.
            if True, the timestamp fields will be converted to human-readable date-time strings. And some fields will be excluded.(text, embedding, user_id, Parent Task, Subtasks)
            else the timestamp fields will be returned as is.
        Returns:
        dict: The task or subtask document if found, or None if not found.
        """
        try:
            if need_to_prompt:
                result = self.collection.find_one(
                {
                        "_id": ObjectId(document_id),
                        "user_id": user_id
                     },
                    {"text": 0, "embedding": 0, "user_id": 0, "Parent Task": 0, "Subtasks": 0, "Type": 0}
                )
            else:
                result = self.collection.find_one(
                    {
                        "_id": ObjectId(document_id),
                        "user_id": user_id
                    },
                    {"text": 0, "embedding": 0, "user_id": 0}
                )
            if result:
                if need_to_prompt:
                    result["Deadline"] = self.timestamp_to_date(result["Deadline"], "%Y-%m-%d %H:%M")
                    if result["Start Time"] != "":
                        result["Start Time"] = self.timestamp_to_date(result["Start Time"], "%Y-%m-%d %H:%M")
                return result
            else:
                print("Document not found")
                return None
        except Exception as e:
            print("Error:", e)
            return None

    def find_by_status(self,status, user_id, need_to_prompt = False):
        """
        Finds tasks or subtasks by their status.
        status (int): The status value to match.
        user_id (int): The user ID associated with the tasks.
        need_to_prompt (bool): A flag indicating whether the found tasks should be prompted to the user.
            if True, the timestamp fields will be converted to human-readable date-time strings.
            else the timestamp fields will be returned as is.
        returns:
        list: A list of tasks or subtasks with the matching
        """
        try:
            if need_to_prompt:
                results = self.collection.find(
                    {"Status": status, "user_id": user_id},
                    {"text": 0, "embedding": 0, "Subtasks": 0, "Parent Task": 0, "user_id": 0, "Type": 0}
                )
            else:
                results = self.collection.find(
                    {"Status": status, "user_id": user_id},
                    {"text": 0, "embedding": 0, "user_id": 0}
                )
            tasks = []
            for result in results:
                if need_to_prompt:
                    result["Deadline"] = self.timestamp_to_date(result["Deadline"], "%Y-%m-%d %H:%M")
                    if result["Start Time"] != "":
                        result["Start Time"] = self.timestamp_to_date(result["Start Time"], "%Y-%m-%d %H:%M")
                tasks.append(result)
            return tasks
        except Exception as e:
            print("Error:", e)
            return []

    def get_all_tasks(self,user_id,need_to_prompt = False):
        """
        Fetches all tasks and subtasks from the database.
        user_id (int): The user ID associated with the tasks.
        need_to_prompt (bool): A flag indicating whether the found tasks should be prompted to the user.
            if True, the timestamp fields will be converted to human-readable date-time strings. Also, some fields will be excluded.(text, embedding, user_id, Parent Task, Subtasks)
            else the timestamp fields will be returned as is.
        Returns:
        list: A list of tasks or subtasks.
        """
        try:
            if need_to_prompt:
                results = self.collection.find(
                    {"user_id": user_id},
                    {"text": 0, "embedding": 0, "Subtasks": 0, "Parent Task": 0, "user_id": 0, "Type": 0}
                )
            else:
                results = self.collection.find(
                    {"user_id": user_id},
                    {"text": 0, "embedding": 0}
                )
            tasks = []
            for result in results:
                if need_to_prompt:
                    result["Deadline"] = self.timestamp_to_date(result["Deadline"], "%Y-%m-%d %H:%M")
                    if result["Start Time"] != "":
                        result["Start Time"] = self.timestamp_to_date(result["Start Time"], "%Y-%m-%d %H:%M")
                tasks.append(result)
            return tasks
        except Exception as e:
            print("Error:", e)
            return []

    def get_task_id(self, task_title, deadline, user_id):
        """
        Fetches the document ID of a task by its title.
        task_title (str): The title of the task to find.
        user_id (int): The user ID associated with the task.
        deadline (str): The deadline date in timestamp format.
        Returns:
        str: The document ID of the task if found, or None if not found.
        """
        try:
            result = self.collection.find_one(
                {
                    "Title": task_title,
                    "user_id": user_id,
                    "Deadline": deadline
                },
                {"_id": 1}
            )
            if result:
                return str(result["_id"])
            else:
                print("Task not found")
                return None
        except Exception as e:
            print("Error:", e)
            return None

    def get_tasks_need_to_reschedule(self, user_id, reschedule_time, need_to_prompt=False):
        """
        Fetches tasks that need to be rescheduled based on the reschedule time.
        user_id (int): The user ID associated with the tasks.
        reschedule_time (int): The reschedule time as a timestamp.
        need_to_prompt (bool): Whether to include additional fields in the response.
        """
        filter_query = {
            "Start Time": {"$lt": reschedule_time},
            "user_id": user_id,
            "Status": {"$ne": 2}  # Status not completed
        }
        if need_to_prompt:
            projection = {"text": 0, "embedding": 0, "user_id": 0, "Parent Task": 0, "Subtasks": 0, "Type": 0}
        else:
            projection = {"text": 0, "embedding": 0, "user_id": 0}

        try:
            results = self.collection.find(filter_query, projection)
            tasks = []
            for result in results:
                if need_to_prompt:
                    result["Deadline"] = self.timestamp_to_date(result["Deadline"], "%Y-%m-%d %H:%M")
                    if result["Start Time"] != "":
                        result["Start Time"] = self.timestamp_to_date(result["Start Time"], "%Y-%m-%d %H:%M")
                tasks.append(result)

            return tasks
        except Exception as e:
            print("Get Tasks Need To Reschedule Error:", e)
            return []

    def get_overdue_tasks(self, user_id, current_time, need_to_prompt=False):
        """
        Fetches tasks that are overdue based on the current time.
        user_id (int): The user ID associated with the tasks.
        current_time (str): The current time in timestamp
        """
        query = []
        query.append({
                "Deadline": {"$lt": current_time},
                "UserID": user_id,
                "Status": {"$nin": [2, 20]}  # Status not completed
            })
        if need_to_prompt:
            query.append({
                "text": 0, "embedding": 0, "user_id": 0, "Parent Task": 0, "Subtasks": 0, "Type": 0
            })
        else:
            query.append({
                "text": 0, "embedding": 0, "user_id": 0
            })
        try:
            results = self.collection.find(query)
            tasks = []
            for result in results:
                if need_to_prompt:
                    result["Deadline"] = self.timestamp_to_date(result["Deadline"], "%Y-%m-%d %H:%M")
                    if result["Start Time"] != "":
                        result["Start Time"] = self.timestamp_to_date(result["Start Time"], "%Y-%m-%d %H:%M")
                tasks.append(result)
            return tasks
        except Exception as e:
            print("Get Overdue Tasks Error:", e)
            return []



    # ----------------------------- update --------------------------------
    # TODO: update
    def update_status(self,user_id,document_id,new_status):
        """
        Updates the status of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_status (int): The new status value to set.
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Status": new_status
                    }
                }
            )
            if result.modified_count > 0:
                print("Status updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Error:", e)
            return False


    def update_deadline(self,user_id,document_id,new_deadline):
        """
        Updates the deadline of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_deadline (str): The new deadline date in timestamp format.
        """
        try:
            new_deadline = self.date_to_timestamp(new_deadline, "%Y%m%d%H%M")
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Deadline": new_deadline
                    }
                }
            )
            if result.modified_count > 0:
                print("Deadline updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Error:", e)
            return False

    def update_title(self,user_id,document_id,new_title):
        """
        Updates the title of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_title (str): The new title to set.
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Title": new_title
                    }
                }
            )
            if result.modified_count > 0:
                print("Title updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Title Error:", e)
            return False

    def update_description(self,user_id,document_id,new_description):
        """
        Updates the description of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_description (str): The new description to set.
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Description": new_description
                    }
                }
            )
            if result.modified_count > 0:
                print("Description updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Description Error:", e)
            return False

    def update_subtasks(self,user_id,document_id, new_subtasks, override=False):
        """
        Updates the subtasks of a parent task.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the parent task to update.
        new_subtasks (list): The new list of subtasks id to set.
        override (bool): A flag indicating whether to override the existing subtasks.
        """
        try:
            if override:
                result = self.collection.update_one(
                    {
                        "_id": ObjectId(document_id),
                        "user_id": user_id
                    },
                    {
                        "$set": {
                            "Subtasks": new_subtasks
                        }
                    }
                )
            else:
                result = self.collection.update_one(
                    {
                        "_id": ObjectId(document_id),
                        "user_id": user_id
                    },
                    {
                        "$push": {
                            "Subtasks": {
                                "$each": new_subtasks
                            }
                        }
                    }
                )
            if result.modified_count > 0:
                print("Subtasks updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Subtasks Error:", e)
            return False

    def update_parent_task(self,user_id,document_id,new_parent_task):
        """
        Updates the parent task of a subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the subtask to update.
        new_parent_task (list): The new parent task details to set.
        """
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Parent Task": new_parent_task
                    }
                }
            )
            if result.modified_count > 0:
                print("Parent task updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Parent Task Error:", e)
            return False

    def update_start_time(self,user_id,document_id,new_start_time, time_format):
        """
        Updates the start time of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_start_time (str): The new start time to set.
        time_format (str): The format of the new start time. e.g., "%Y%m%d%H%M"
        """
        try:
            new_start_time = self.date_to_timestamp(new_start_time, time_format)
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Start Time": new_start_time
                    }
                }
            )
            if result.modified_count > 0:
                print("Start time updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Start Time Error:", e)
            return False

    def update_deadline(self,user_id,document_id,new_deadline,time_format):
        """
        Updates the deadline of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_deadline (str): The new deadline date in timestamp format.
        time_format (str): The format of the new deadline. e.g., "%Y%m%d%H%M"
        """
        try:
            new_deadline = self.date_to_timestamp(new_deadline, time_format)
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Deadline": new_deadline
                    }
                }
            )
            if result.modified_count > 0:
                print("Deadline updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Deadline Error:", e)
            return False

    def update_rescheduled_task(self,user_id,document_id,new_start_time,new_deadline,new_status,time_format = ""):
        """
        Updates the start time, deadline, and status of a task or subtask.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to update.
        new_start_time (str): The new start time to set.
        new_deadline (str): The new deadline date in timestamp format.
        new_status (int): The new status value to set.
        time_format (str): The format of the new start time and deadline. e.g., "%Y%m%d%H%M"
        """
        try:
            if time_format != "":
                new_start_time = self.date_to_timestamp(new_start_time, time_format)
                new_deadline = self.date_to_timestamp(new_deadline, time_format)
            result = self.collection.update_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                },
                {
                    "$set": {
                        "Start Time": new_start_time,
                        "Deadline": new_deadline,
                        "Status": new_status
                    }
                }
            )
            if result.modified_count > 0:
                print("Task updated successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Update Task Error:", e)
            return False

    # ----------------------------- delete --------------------------------
    def delete_task(self,user_id,document_id):
        """
        Deletes a task or subtask from the database.
        user_id (int): The user ID associated with the task.
        document_id (str): The ID of the task or subtask to delete.
        """
        try:
            result = self.collection.delete_one(
                {
                    "_id": ObjectId(document_id),
                    "user_id": user_id
                }
            )
            if result.deleted_count > 0:
                print("Task deleted successfully.")
                return True
            else:
                print("No matching document found.")
                return False
        except Exception as e:
            print("Delete Task Error:", e)
            return False


if __name__ == '__main__':
    database = DeadlineDatabase("Deadlines")
    # deadlines = [
    #     {
    #         "Title": "OS-CoPilot Demo Presentation",
    #         "Description": "Prepare a demo presentation for OS-CoPilot. Include coding, presentation slides, and a live demo.",
    #         "Start Time" :"",
    #         "Deadline": "202411251900",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     },
    #     {
    #         "Title": "Data Mining Assignment2",
    #         "Description": "3 subtasks: 1. Evaluate car sales data via Weka. 2. Assoication rule mining. 3. Clustering.",
    #         "Start Time":"",
    #         "Deadline": "202411272359",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     },
    #     {
    #         "Title": "CV Reviewer",
    #         "Description": "Review the CVs of the applicants for the Data Scientist position.",
    #         "Start Time":"",
    #         "Deadline": "202411301700",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     },
    #     {
    #         "Title": "Weekend Getaway Planning",
    #         "Description": "Plan and finalize the itinerary for a weekend getaway with friends. Book transportation and accommodation.",
    #         "Startime":"",
    #         "Deadline": "202412102000",
    #         "Status": 0,
    #         "Subtasks": [],
    #         "Parent Task": [],
    #     },
    #     {
    #         "Title": "Team Meeting Presentation",
    #         "Description": "Prepare a brief presentation for the team's weekly sync. Include project updates and upcoming plans.",
    #         "Start Time":"",
    #         "Deadline": "202412051000",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     },
    #     {
    #         "Title": "Christmas Holiday Planning",
    #         "Description": "Plan the Christmas holiday activities, including gift shopping, travel arrangements, and dinner preparation.",
    #         "Start Time":"",
    #         "Deadline": "202412201800",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     },
    #     {
    #         "Title": "Deep Learning Course Final Exam",
    #         "Description": "The final examination on deep learning, including basic information, CNN, GNN, and RNN.",
    #         "Start Time": "",
    #         "Deadline": "202412141830",
    #         "Subtasks": [],
    #         "Parent Task": [],
    #         "Status": 0,
    #     }
    # ]
    # for deadline in deadlines:
    #     id = database.insert_one_task(deadline, 1, 0)
    #     print(id)

    # deadlines_db = DeadlineDatabase("Deadlines")
    # id = "67404416e8169705f9374a79"
    # result = deadlines_db.find_by_id(id)
    # print(result)
    # uuid = deadlines_db.insert_one_task(deadline, 1, 0)

    deadlines_db = DeadlineDatabase("Deadlines")
    deadlines_db.update_rescheduled_task(2, "674199564453b485732c7734", "202411241200", "202411261300", 1, "%Y%m%d%H%M")

