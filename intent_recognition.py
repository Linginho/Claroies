# intent_recognition.py

from openai import AzureOpenAI
import pandas as pd
from langchain.vectorstores import FAISS
from langchain_openai.embeddings import AzureOpenAIEmbeddings
import configparser
import json
from netcalculator import NETCalorieCalculator
from access_db import Userdata, Dailydata
from datetime import datetime
import os

class IntentRecognition:
    def __init__(self, user_id):
        self.user_id = user_id

        # 初始化配置
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # 初始化 Azure OpenAI
        self.client = AzureOpenAI(
            api_key=self.config["AzureOpenAI"]["API_KEY"],
            api_version=self.config["AzureOpenAI"]["API_VERSION"],
            azure_endpoint=self.config["AzureOpenAI"]["API_BASE"],
        )

        # 初始化 Azure OpenAI Embeddings
        self.embedding_function = AzureOpenAIEmbeddings(
            deployment=self.config["AzureOpenAI_Embedding"]["DEPLOYMENT_NAME_TEXT_EMBEDDING_ADA_002"],
            model="text-embedding-ada-002",
            azure_endpoint=self.config["AzureOpenAI_Embedding"]["API_BASE"],
            openai_api_key=self.config["AzureOpenAI_Embedding"]["API_KEY"],
            openai_api_type="azure",
            openai_api_version=self.config["AzureOpenAI_Embedding"]["API_VERSION"],
            chunk_size=1000,
        )

        # 初始化 FAISS 向量資料庫
        if not os.path.exists("faiss_exercise_id_index"):
            print("索引不存在，正在建立索引...")
            self.faiss_index = self.build_faiss_index_from_csv(csv_file='exercisename.csv')
        else:
            self.faiss_index = self.load_faiss_index()

        # 初始化使用者資料
        self.user_data = Userdata(self.user_id)
        self.user_record = self.user_data.search_data('u_id', self.user_id)

        if not self.user_record:
            # 如果使用者不存在，正在建立使用者...
            print("使用者不存在，正在建立使用者...")
            self.user_data.add_data(
                u_id=self.user_id,
                name='新使用者',
                gender=True,  # 根據需要設定性別，True為男性，False為女性
                age=30,
                weight=70.0,
                height=175.0,
                activity_level=1.2
            )
            # 重新獲取使用者資料
            self.user_record = self.user_data.search_data('u_id', self.user_id)

        # 將使用者記錄轉換為字典
        column_names = self.user_data.get_all_columns()
        self.user_dict = dict(zip(column_names, self.user_record))

    # 讀取 CSV 文件
    def load_exercise_data(self, csv_file):
        return pd.read_csv(csv_file)

    # 創建 FAISS 向量資料庫
    def build_faiss_index_from_csv(self, csv_file):
        exercise_data = self.load_exercise_data(csv_file)
        exercise_data["exercise_name"] = exercise_data["exercise_name"].astype(str)

        metadatas = [
            {
                "exercise_name": row["exercise_name"],
                "M_id": row["M_id"],
                "W_id": row["W_id"]
            }
            for _, row in exercise_data.iterrows()
        ]

        faiss_index = FAISS.from_texts(
            texts=exercise_data["exercise_name"].tolist(),
            embedding=self.embedding_function,
            metadatas=metadatas
        )
        faiss_index.save_local("faiss_exercise_id_index", "index")
        return faiss_index

    # 加載 FAISS 向量資料庫
    def load_faiss_index(self):
        return FAISS.load_local(
            "faiss_exercise_id_index",
            "index",
            embedding=self.embedding_function,
            allow_dangerous_serialization=True
        )

    # 計算速度描述的函數
    def calculate_speed_description(self, exercise_name, duration_minutes, distance):
        if exercise_name == "跑步" and distance:
            total_seconds = (duration_minutes * 60) / distance
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            speed_description = f"每公里耗時{minutes}分鐘{seconds}秒"
            return speed_description
        elif exercise_name == "騎自行車" and distance:
            speed = distance / (duration_minutes / 60)
            speed_description = f"{speed:.1f}公里/小時"
            return speed_description
        else:
            return ""

    # LLM 識別意圖並提取運動資訊
    def azure_openai(self, user_input):
        message_text = [
            {
                "role": "system",
                "content": """
你會根據輸入判斷行為類型。行為類型包括：記錄飲食，記錄運動。
如果提到食物，應返回「記錄飲食」；如果提到運動，應返回「記錄運動」。
你還會從輸入中提取運動名稱、持續時間、距離，並計算速度描述（根據運動類型）。
請確保返回的速度描述與運動常用的速度表示方式一致，例如：跑步的每公里耗時，騎自行車的公里/小時速度。
例如，若使用者輸入「我今天跑步兩小時，跑了8公里」，你應該返回：持續時間為120分鐘，距離為8公里，速度描述為「每公里耗時15分鐘」。
""",
            },
            {"role": "user", "content": user_input}
        ]

        functions = [{
            "name": "get_exercise_info",
            "description": "識別運動類型並提取相關資訊",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "行為類型：記錄運動"},
                    "exercise_name": {"type": "string", "description": "運動名稱"},
                    "duration_minutes": {"type": "integer", "description": "運動持續時間，單位：分鐘"},
                    "distance": {"type": "number", "description": "運動距離，單位：公里（選填）"},
                    "needs_distance": {"type": "boolean", "description": "是否需要距離參數"},
                    "speed_description": {"type": "string", "description": "速度描述，例如「每公里耗時15分鐘」，包含計算後的速度資訊"}
                },
                "required": ["intent", "exercise_name", "duration_minutes"],
            },
        }]

        completion = self.client.chat.completions.create(
            model=self.config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
            messages=message_text,
            functions=functions,
            max_tokens=800,
        )
        completion_message = completion.choices[0].message

        if completion.choices[0].finish_reason == "function_call":
            this_arguments = json.loads(completion_message.function_call.arguments)
            
            # 添加調試輸出
            print("LLM 返回的參數：", this_arguments)
            
            return (
                this_arguments["intent"],
                this_arguments["exercise_name"],
                this_arguments["duration_minutes"],
                this_arguments.get("distance", None),
                this_arguments.get("needs_distance", False),
                this_arguments.get("speed_description", "")
            )
        return None, None, None, None, False, ""

    # 處理使用者輸入並返回結果
    def process_input(self, user_input):
        intent, exercise_name, duration_minutes, distance, needs_distance, speed_description = self.azure_openai(user_input)
        if intent == "記錄運動":
            if duration_minutes == 0:
                return f"請提供{exercise_name}的持續時間，以便準確計算卡路里。範例：今天{exercise_name}兩小時"

            if needs_distance and distance is None:
                return f"請提供{exercise_name}的距離，以便準確計算卡路里。範例：今天{exercise_name}兩小時，大概十公里"

            if not speed_description:
                speed_description = self.calculate_speed_description(exercise_name, duration_minutes, distance)
                print(f"手動計算的速度描述: {speed_description}")

            print(f"識別到的運動: {exercise_name}, 持續時間: {duration_minutes}分鐘, 距離: {distance}公里, 速度描述: {speed_description}")

            # 使用 speed_description 生成查詢
            if speed_description:
                query = f"{exercise_name}，{speed_description}"
            else:
                query = f"{exercise_name}"

            # 搜索相似的運動
            results = self.faiss_index.similarity_search_with_score(query, k=1)
            exercise_metadata = results[0][0].metadata

            # 獲取 gender 並轉換為布林值
            gender = self.user_dict['gender']
            gender = bool(gender)

            # 根據性別選擇對應的 exercise_id
            exercise_id = exercise_metadata['M_id'] if gender else exercise_metadata['W_id']

            calculator = NETCalorieCalculator(self.user_id)
            if not calculator.get_user_data():
                return "無法獲取使用者資料，程式終止。"

            calculator.set_exercise_info(duration_minutes, distance)
            calories_burned = calculator.fetch_calories_from_website(exercise_id, exercise_name)

            print(f"消耗卡路里: {calories_burned}")

            # === 將運動資料儲存到資料庫 ===
            # 建立 Dailydata 實例，使用與 Userdata 相同的資料庫
            daily_data = Dailydata(self.user_id)

            # 取得當前日期時間
            data_time = datetime.now().isoformat()

            # 呼叫 add_data 方法，將資料插入到資料庫
            daily_data.add_data(
                u_id=self.user_id,
                data_time=data_time,
                food_name="",  # 這裡沒有食物，故為空字串
                food_calories=0,  # 食物卡路里為 0
                exercise_name=exercise_name,
                exercise_duration=duration_minutes  # 持續時間（分鐘）
            )

            print("成功將運動資料儲存到資料庫。")
            return f"您進行了 {exercise_name}，持續時間為 {duration_minutes} 分鐘，消耗了約 {calories_burned} 卡路里。"

        else:
            return "無法識別的行為類型。"

