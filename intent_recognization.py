# intent_recognition.py

import sys
import configparser
import requests, json
from openai import AzureOpenAI
from netcalculator import NETCalorieCalculator  # 導入卡路里計算器類

# 初始化Azure OpenAI
config = configparser.ConfigParser()
config.read('config.ini')
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["API_KEY"],
    api_version=config["AzureOpenAI"]["API_VERSION"],
    azure_endpoint=config["AzureOpenAI"]["API_BASE"],
)

# 識別意圖並提取運動資訊
def azure_openai(user_input):
    message_text = [
        {
            "role": "system",
            "content": """
            你會根據輸入判斷行為類型。行為類型包括: 記錄飲食, 記錄運動。
            如果提到食物，應返回“記錄飲食”；如果提到運動，應返回“記錄運動”。
            你還會從輸入中提取運動名稱和持續時間。
            """,
        },
        {   
            "role": "user", 
            "content": user_input
        }
    ]

    functions = [
        {
            "name": "get_exercise_info", 
            "description": "識別運動類型並提取相關資訊", 
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "行為類型: 記錄運動"
                    },
                    "exercise_name": {
                        "type": "string",
                        "description": "運動名稱，如跑步、游泳等"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "運動持續時間，以分鐘為單位"
                    }
                },
                "required": ["intent", "exercise_name", "duration_minutes"],
            },
        }
    ]

    completion = client.chat.completions.create(    
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
        messages=message_text,
        functions=functions,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )

    completion_message = completion.choices[0].message

    if completion.choices[0].finish_reason == "function_call":
        this_arguments = json.loads(completion_message.function_call.arguments)
        result_intent = this_arguments["intent"]
        exercise_name = this_arguments["exercise_name"]
        duration_minutes = this_arguments["duration_minutes"]
        return result_intent, exercise_name, duration_minutes
    else:
        return None, None, None

# 主函數，結合意圖識別與卡路里計算
def main():
    user_id = "user_001"
    user_input = "我今天跳繩跳了1小時"
    
    # 調用Azure OpenAI識別意圖並提取運動資訊
    intent, exercise_name, duration_minutes = azure_openai(user_input)

    if intent == "記錄運動":
        print(f"識別到的運動: {exercise_name}, 持續時間: {duration_minutes}分鐘")

        # 初始化卡路里計算器
        calculator = NETCalorieCalculator(user_id)
        calculator.set_exercise_duration(duration_minutes)
        result_message = calculator.calculate_calories(exercise_name)

        if result_message:
            print(result_message)  # 回傳訊息給使用者

if __name__ == '__main__':
    main()
