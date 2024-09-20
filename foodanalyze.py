import logging
import configparser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from access_db import Dailydata

class FoodCalorieAnalyzer:
    def __init__(self, user_id):
        self.user_id = user_id

        # 初始化配置
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # 初始化 Google Gemini
        self.client = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=self.config["Gemini"]["API_KEY"]
        )

    def analyze_food_with_gemini(self, user_input):
        """
        使用 Google Gemini 直接分析食物描述並估算卡路里
        """
        prompt = f"""
        你是一位專業的營養師，請根據台灣地區民眾普遍飲食，給出以下食物的平均卡路里，無需精確熱量：
        {user_input}

        如果你能給出一個估算的卡路里數，請直接提供。如果無法精確計算，根據一般飲食習慣估算一個大致的卡路里。
        不要給一個範圍，請給出一個具體的數字。
        然後也可以繼續詢問用戶請求更多訊息，如大致的份量以及內容物。

        """

        try:
            response = self.client.invoke([HumanMessage(content=prompt)])
            calorie_estimate = response.content.strip()
            logging.info(f"Gemini 返回的卡路里估算: {calorie_estimate}")
            return calorie_estimate
        except Exception as e:
            logging.error(f"Google Gemini 分析失敗: {e}")
            return "無法估算熱量，請再試一次。"

    def store_food_calories(self, food_name, total_calories):
        """
        將食物總熱量存入資料庫
        """
        daily_data = Dailydata(self.user_id)
        try:
            daily_data.add_data(
                food_name=food_name,
                food_calories=total_calories,
                exercise_name="",
                exercise_duration=0,
                calories_burned=0
            )
            logging.info(f"已將 {food_name} 的熱量數據存入資料庫: {total_calories} 卡路里")
        except Exception as e:
            logging.error(f"存入資料庫失敗: {e}")

    def handle_food_input(self, user_input):
        """
        綜合處理食物熱量輸入，直接透過 Google Gemini 進行分析，返回卡路里估算並存入資料庫
        """
        # Step 1: 使用 Google Gemini 分析食物描述並估算卡路里
        calorie_estimate = self.analyze_food_with_gemini(user_input)

        # Step 2: 存入資料庫
        self.store_food_calories(user_input, calorie_estimate)

        # Step 3: 簡化回覆訊息
        if "無法估算熱量" not in calorie_estimate:
            return f"您所吃的 {user_input} 含有 {calorie_estimate}。"
        else:
            return "無法估算該食物的熱量，請再提供更多資訊或嘗試其他食物描述。"

if __name__ == "__main__":
    user_id = "example_user"  # 替換為真實的用戶ID
    analyzer = FoodCalorieAnalyzer(user_id)

    # 模擬使用者輸入
    user_input = "我吃了一碗牛肉麵"
    
    # 處理輸入，並回應結果
    result = analyzer.handle_food_input(user_input)
    print(result)