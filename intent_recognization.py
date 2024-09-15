# intent_recognition.py
from openai import AzureOpenAI
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
import configparser
import json
from netcalculator import NETCalorieCalculator
from access_db import Userdata

# 初始化Azure OpenAI
config = configparser.ConfigParser()
config.read('config.ini')
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["API_KEY"],
    api_version=config["AzureOpenAI"]["API_VERSION"],
    azure_endpoint=config["AzureOpenAI"]["API_BASE"],
)

# 讀取CSV文件
def load_exercise_data(csv_file):
    return pd.read_csv(csv_file)

# 建立FAISS向量資料庫
def build_faiss_index_from_csv(csv_file):
    exercise_data = load_exercise_data(csv_file)
    config.read("config.ini")

    embedding_function = AzureOpenAIEmbeddings(
        azure_deployment=config["AzureOpenAI_Embedding"]["DEPLOYMENT_NAME_TEXT_EMBEDDING_ADA_002"],
        openai_api_version=config["AzureOpenAI_Embedding"]["API_VERSION"],
        azure_endpoint=config["AzureOpenAI_Embedding"]["API_BASE"],
        api_key=config["AzureOpenAI_Embedding"]["API_KEY"],
    )

    metadatas = [{"exercise_name": row["exercise_name"], "M_id": row["M_id"], "W_id": row["W_id"]} for _, row in exercise_data.iterrows()]
    faiss_index = FAISS.from_texts(exercise_data["exercise_name"].tolist(), embedding_function, metadatas)
    faiss_index.save_local("faiss_exercise_id_index", "index")
    return faiss_index

# 加載FAISS向量資料庫
def load_faiss_index():
    return FAISS.load_local("faiss_exercise_id_index", "index")

# LLM 識別意圖並提取運動資訊
def azure_openai(user_input):
    message_text = [
        {
            "role": "system",
            "content": """
            你會根據輸入判斷行為類型。行為類型包括: 記錄飲食, 記錄運動。
            如果提到食物，應返回“記錄飲食”；如果提到運動，應返回“記錄運動”。
            你還會從輸入中提取運動名稱、持續時間和距離。
            如果運動是需要距離的（如跑步或單車），但未提供距離，你會告知需要距離。
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
                "intent": {"type": "string", "description": "行為類型: 記錄運動"},
                "exercise_name": {"type": "string", "description": "運動名稱"},
                "duration_minutes": {"type": "integer", "description": "運動持續時間"},
                "distance": {"type": "number", "description": "運動距離（選填）"},
                "needs_distance": {"type": "boolean", "description": "是否需要距離參數"}
            },
            "required": ["intent", "exercise_name", "duration_minutes"],
        },
    }]

    completion = client.chat.completions.create(
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
        messages=message_text,
        functions=functions,
        max_tokens=800,
    )
    completion_message = completion.choices[0].message

    if completion.choices[0].finish_reason == "function_call":
        this_arguments = json.loads(completion_message.function_call.arguments)
        return (this_arguments["intent"], this_arguments["exercise_name"],
                this_arguments["duration_minutes"], this_arguments.get("distance", None),
                this_arguments.get("needs_distance", False))
    return None, None, None, None, False

# 檢索最相似的運動項目
def search_similar_exercise(faiss_index, exercise_name):
    results = faiss_index.similarity_search_with_score(exercise_name, 1)  # 取最相似的
    return results[0][0].metadata

# 主函數，結合意圖識別與卡路里計算
def main():
    user_input = "我今天跑步5公里"

    intent, exercise_name, duration_minutes, distance, needs_distance = azure_openai(user_input)
    if intent == "記錄運動":
        if duration_minutes == 0:  # 檢查是否提供了持續時間
            print(f"請提供{exercise_name}的持續時間，以便準確計算卡路里。")
            return

        if needs_distance and distance is None:
            print(f"請提供{exercise_name}的距離，以便準確計算卡路里。")
            return

        print(f"識別到的運動: {exercise_name}, 持續時間: {duration_minutes}分鐘, 距離: {distance}公里")

        faiss_index = load_faiss_index()
        exercise_metadata = search_similar_exercise(faiss_index, exercise_name)

        user_data = Userdata("user_001")
        exercise_id = exercise_metadata['M_id'] if user_data.gender else exercise_metadata['W_id']

        calculator = NETCalorieCalculator("user_001")
        calculator.set_exercise_info(duration_minutes, distance)
        calories_burned = calculator.fetch_calories_from_website(exercise_id, exercise_name)

        print(f"消耗卡路里: {calories_burned}")


if __name__ == '__main__':
    main()
