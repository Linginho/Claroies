import configparser
import json
import re
from openai import AzureOpenAI
from access_db import Dailydata  # 匯入資料庫操作

class FoodCalorieAnalyzer:
    def __init__(self, user_id, config_file='config.ini'):
        # Initialize user_id and config
        self.user_id = user_id
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Initialize Azure OpenAI Client
        self.client = AzureOpenAI(
            api_key=self.config["AzureOpenAI"]["API_KEY"],
            api_version=self.config["AzureOpenAI"]["API_VERSION"],
            azure_endpoint=self.config["AzureOpenAI"]["API_BASE"],
        )

    # 提取數字
    def extract_numbers(self, input_string):
        numbers = re.findall(r'\d+', input_string)
        return numbers

    # 提取大卡前的10個字符
    def extract_before_calories(self, input_string, keyword="大卡", num_chars=15):
        match = re.search(rf".{{0,{num_chars}}}{keyword}", input_string)
        if match:
            return match.group(0)[:-len(keyword)]
        else:
            return ""

    # 有function_call: 食物名和份量辨識
    def food_recognization(self, user_input):
        message_text = [
            {
                "role": "system",
                "content": "",
            },
            {   
                "role": "user", 
                "content": user_input
            },
        ]
        message_text[0]["content"] += "請一律用繁體中文回答。"
        
        functions = [
            {
                "name": "get_food_info",
                "description": "獲取食物名和份量",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "食物名": {
                            "type": "string", 
                            "description": "食物名稱"
                        }, 
                        "食物份量": {
                            "type": "string",
                            "description": "食物的份量，如：10顆、一碗、一盤、重量等", 
                        },
                    },
                "required": ["食物名", "食物份量"], 
                },
            }
        ]
        
        completion = self.client.chat.completions.create(    
            model=self.config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
            messages=message_text,
            functions=functions,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )

        if completion.choices[0].finish_reason == "function_call": 
            this_arguments = json.loads(completion.choices[0].message.function_call.arguments)
            return this_arguments["食物名"], this_arguments["食物份量"]
        else:
            return None, None

    # 向大LLM問卡路里
    def calories_from_llm(self, food_name, portion):
        message_text = [
            {
                "role": "system",
                "content": "",
            },
            {   
                "role": "user", 
                "content": f"{food_name}{portion}為多少大卡"
            },
        ]
        message_text[0]["content"] += "請給我一個平均值並用簡短的回覆。"
        
        completion = self.client.chat.completions.create(    
            model=self.config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
            messages=message_text,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )
        
        completion_content = self.extract_before_calories(completion.choices[0].message.content)
        completion_content = self.extract_numbers(completion_content)
        
        calories = (int(completion_content[0]) + int(completion_content[1])) / 2 if len(completion_content) > 1 else completion_content[0]
        return str(calories)

    # 將結果存入資料庫
    def store_food_calories(self, food_name, calories):
        daily_data = Dailydata(self.user_id)
        try:
            daily_data.add_data(
                food_name=food_name,
                food_calories=calories,
                exercise_name="",
                exercise_duration=0,
                calories_burned=0
            )
            print(f"已將 {food_name} 的熱量數據存入資料庫: {calories} 大卡")
        except Exception as e:
            print(f"存入資料庫失敗: {e}")

    # 完整流程: 食物辨識 + 卡路里計算 + 存入資料庫
    def analyze_and_store_food_calories(self, user_input):
        food_name, portion = self.food_recognization(user_input)
        if food_name and portion:
            food_calories = self.calories_from_llm(food_name, portion)
            self.store_food_calories(food_name, food_calories)
            return f"您所吃的 {food_name}{portion} 含有 {food_calories} 大卡，已幫您紀錄。"
        else:
            return "無法提取食物名稱或份量，請重新輸入。"

if __name__ == "__main__":
    user_id = "example_user"
    user_input = "我今天吃了一碗拉麵"
    
    analyzer = FoodCalorieAnalyzer(user_id)
    result_message = analyzer.analyze_and_store_food_calories(user_input)
    print(result_message)