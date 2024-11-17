from cmath import isnan

# from matplotlib.backend_tools import cursors
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
import pandas as pd
from datetime import datetime,timedelta
from sqlalchemy.dialects.mysql import insert

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

    def insert(self, data):
        i = 0
        insert_count = 0
        for item in data:
            i = i+1
            for key, value in item.items():
                text = key + ": " + str(value)
            embedding = self.get_embedding(text)
            document = {**item, "text": text, "embedding": embedding}
            try:
                self.collection.insert_one(document)
                insert_count = insert_count + 1
            except Exception as e:
                print(f"Error inserting document {i}: {e}")
                continue
        print(f"Inserted {insert_count} documents into the collection.")

    def find_by_deadline(self, deadline_str):
        """
        Finds documents with a deadline matching or earlier than the specified deadline.

        Parameters:
        deadline (str): The deadline date in ISO 8601 format (e.g., "2024-11-30").

        Returns:
        list: A list of matching documents.
        """
        try:
            # 将截止日期字符串转换为 datetime 对象
            deadline = datetime.strptime(deadline_str, "%Y%m%d%H%M")
            now = datetime.now()

            # 计算从当前时间到截止日期的持续时长（分钟）
            duration = (deadline - now).total_seconds() / 60

            # 使用 MongoDB 聚合查询最大值和最小值
            aggregation_pipeline = [
                {
                    "$addFields": {
                        "Duration": {
                            "$cond": [
                                {"$and": [{"$ifNull": ["$Start Time", False]}, {"$ifNull": ["$End Time", False]}]},
                                {
                                    "$divide": [
                                        {"$subtract": [
                                            {"$dateFromString": {"dateString": "$End Time", "format": "%Y%m%d%H%M"}},
                                            {"$dateFromString": {"dateString": "$Start Time", "format": "%Y%m%d%H%M"}}
                                        ]},
                                        60 * 1000  # 转换为分钟
                                    ]
                                },
                                None
                            ]
                        }
                    }
                },
                {"$match": {"Duration": {"$ne": None}}},  # 排除没有持续时间的记录
                {
                    "$group": {
                        "_id": None,
                        "max_duration": {"$max": "$Duration"},
                        "min_duration": {"$min": "$Duration"},
                    }
                }
            ]

            duration_stats = list(self.collection.aggregate(aggregation_pipeline))
            if not duration_stats:
                print("数据库中没有有效的持续时长记录。")
                return []

            max_duration = duration_stats[0]["max_duration"]
            min_duration = duration_stats[0]["min_duration"]

            # 动态调整误差范围
            if duration < min_duration:
                tolerance = max(10, min_duration * 0.1)
            elif duration > max_duration:
                tolerance = max(10, max_duration * 0.1)
            else:
                tolerance = max(10, duration * 0.2)

            # 匹配持续时长与用户输入接近的记录
            results = []
            logs = self.collection.find()
            for log in logs:
                if "Start Time" in log and "End Time" in log:
                    try:
                        start_time = datetime.strptime(log["Start Time"], "%Y%m%d%H%M")
                        end_time = datetime.strptime(log["End Time"], "%Y%m%d%H%M")
                        log_duration = (end_time - start_time).total_seconds() / 60

                        # 打印调试信息
                        print(
                            f"记录 {log['Name']} 的时长: {log_duration:.2f} 分钟, 目标时长: {duration:.2f} 分钟, 容差范围: ±{tolerance:.2f} 分钟")

                        # 判断持续时长是否在容许误差范围内
                        if abs(log_duration - duration) <= tolerance:
                            results.append(log)
                    except Exception as e:
                        print(f"Error processing log: {log}, Error: {e}")
                else:
                    print(f"跳过无效记录: {log}")

            return results

        except Exception as e:
            print(f"Error during find_by_deadline: {e}")
            return []


class DailyLogDatabase(Database):
    def __init__(self, collection_name):
        super().__init__()
        self.collection = self.db[collection_name]

    def insert(self, data):
        i = 0
        insert_count = 0
        for item in data:
            i = i+1
            text = "Activity: "+ str(item["Name"])+", "+"Type: "+ str(item["Type"])
            embedding = self.get_embedding(text)
            document = {**item, "text": text, "embedding": embedding}
            try:
                self.collection.insert_one(document)
                insert_count = insert_count + 1
            except Exception as e:
                print(f"Error inserting document {i}: {e}")
                continue
        print(f"Inserted {insert_count} documents into the collection.")

    def find(self, query, limit = -1):
        cursors = self.collection.find(query)
        cursors = cursors.limit(limit) if limit > 0 else cursors
        response = []
        for cursor in cursors:
            response.append(cursor)
        logs = []
        for item in response:
            log= {}
            for key, value in item.items():
                if key == "Name":
                    log["Active:"] = value
                elif key == "Type":
                    log["Type:"] = value
                elif key == "Start Time":
                    try:
                        date_obj = datetime.strptime(value, "%Y%m%d%H%M")
                        log["Start Time:"] = date_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                elif key == "End Time":
                    try:
                        date_obj = datetime.strptime(value, "%Y%m%d%H%M")
                        log["End Time:"] = date_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                elif key == "Date":
                    try:
                        date_obj = datetime.strptime(value, "%Y%m%d")
                        log["Date:"] = date_obj.strftime("%Y-%m-%d")
                    except:
                        pass
            logs.append(log)
        return logs

class HabitDatabase(Database):
    def __init__(self, collection_name):
        super().__init__()
        self.collection = self.db[collection_name]
    def insert(self, data):
        i = 0
        insert_count = 0
        for item in data:
            i = i+1
            for key, value in item.items():
                text = key + ": " + str(value)
            embedding = self.get_embedding(text)
            document = {**item, "text": text, "embedding": embedding}
            try:
                self.collection.insert_one(document)
                insert_count = insert_count + 1
            except Exception as e:
                print(f"Error inserting document {i}: {e}")
                continue
        print(f"Inserted {insert_count} documents into the collection.")

if __name__ == '__main__':
    data = df = pd.read_csv("./data/datalog1.csv")
    data = df.to_dict(orient='records')
    input_data = []
    for item in data:
        input = {}
        for key, value in item.items():
            starttime = 0
            endtime = 0
            if key == "Name":
                input["Name"] = value
            if key == "类型":
                input["Type"] = value
            if key == "开始时间":
                try:
                    date_obj = datetime.strptime(value, "%B %d, %Y %I:%M %p (GMT+8)")
                    date_obj += timedelta(weeks=7)
                    input["Start Time"] = date_obj.strftime("%Y%m%d%H%M")
                    starttime = int(input["Start Time"])
                except:
                    pass
            if key == "结束时间":
                try:
                    date_obj = datetime.strptime(value, "%B %d, %Y %I:%M %p (GMT+8)")
                    date_obj += timedelta(weeks=7)
                    input["End Time"] = date_obj.strftime("%Y%m%d%H%M")
                    endtime = int(input["End Time"])
                    int["Duration"] = endtime - starttime
                except:
                    pass
            if key == "日期":
                try:
                    date_obj = datetime.strptime(value, "%Y/%m/%d")
                    date_obj += timedelta(weeks=7)
                    input["Date"] = date_obj.strftime("%Y%m%d")
                except:
                    pass
        input_data.append(input)

    log_db = DailyLogDatabase("daily_logs")
    log_db.insert(input_data)