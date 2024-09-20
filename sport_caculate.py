import configparser
from access_db import Userdata, Dailydata  # 匯入資料庫操作
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

# 設定檔讀取
config = configparser.ConfigParser()
config.read("config.ini")

# 初始化 Google Gemini
gemini_client = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    google_api_key=config["Gemini"]["API_KEY"],
    convert_system_message_to_human=True,
)

class CalorieAnalyzer:
    def __init__(self, user_id):
        self.user_id = user_id

    def handle_user_input(self, user_input):
        """
        處理來自 app.py 的用戶輸入，檢查基本資料和運動時間，然後返回簡化結果給 app.py。
        """
        # 步驟 1: 從資料庫抓取用戶基本資料
        userdata = Userdata(self.user_id)
        user_record = userdata.search_data('u_id', self.user_id)

        # 無法取得用戶基本資料，使用預設值
        if not user_record:
            weight = 70  # 預設體重
            reply_message = "無法取得您的基本資料，使用預設體重 70 公斤計算。\n"
        else:
            weight = user_record.get('weight', 70)  # 從資料庫中取得體重，預設 70 公斤
            reply_message = f"使用您的體重 {weight} 公斤進行計算。\n"

        # 步驟 2: 檢查用戶是否輸入了運動時間，否則提醒用戶提供運動時間
        if "分鐘" not in user_input:
            return reply_message + "請提供運動的時間（例如：跑步 30 分鐘）。"

        # 步驟 3: 使用 Google Gemini 分析並返回簡化結果
        result = self.gemini_calculate(user_input, weight)

        # 返回結果給 app.py 推送給用戶
        return result

    def gemini_calculate(self, user_input, weight):
        """
        使用 Google Gemini 分析運動數據並回應用戶。後端存取數據到資料庫，前端僅顯示回應訊息。
        """
        prompt = f"""
        你是一個專業的運動卡路里分析顧問。請從以下輸入中提取關鍵資訊並計算卡路里。

        1. 請從用戶輸入中提取運動名稱、持續時間，並根據 MET 值和體重來計算消耗的卡路里。

        用戶輸入："{user_input}"，用戶體重：{weight} 公斤。

        你的回應應該是簡短的，告訴用戶運動名稱、持續時間和消耗的卡路里，格式如下：
        "運動名稱：<運動名稱>，持續時間：<持續時間> 分鐘，消耗卡路里：<卡路里> 卡路里"。
        """

        try:
            # 使用 Gemini 進行分析
            human_message = HumanMessage(content=prompt)
            result = gemini_client.invoke([human_message])
            response_text = result.content.strip()

            # 假設返回的結果格式為：
            # "運動名稱：跑步，持續時間：30 分鐘，消耗卡路里：300 卡路里"
            
            # 提取關鍵數據
            exercise_name = None
            exercise_duration = None
            calories_burned = None

            # 使用簡單的文本解析
            for line in response_text.split("，"):
                if "運動名稱" in line:
                    exercise_name = line.split("：")[1].strip()
                elif "持續時間" in line:
                    exercise_duration = int(line.split("：")[1].replace("分鐘", "").strip())
                elif "消耗卡路里" in line:
                    calories_burned = int(line.split("：")[1].replace("卡路里", "").strip())

            # 確保提取成功
            if not all([exercise_name, exercise_duration, calories_burned]):
                return "無法提取運動數據，請再試一次。"

            # 後端自動將提取到的數據存入資料庫
            self.store_calorie_data(exercise_name, exercise_duration, calories_burned)

            # 返回 Gemini 回應的結果
            return f"運動名稱：{exercise_name}，持續時間：{exercise_duration} 分鐘，消耗卡路里：{calories_burned} 卡路里"
        
        except Exception as e:
            return f"處理輸入時發生錯誤：{e}"

    def store_calorie_data(self, exercise_name, exercise_duration, calories_burned):
        """
        將運動數據自動存入資料庫，無需用戶干預
        """
        daily_data = Dailydata(self.user_id)
        try:
            daily_data.add_data(
                food_name="",  # 運動記錄無需食物名稱
                food_calories=0,  # 食物卡路里為 0
                exercise_name=exercise_name,  # 運動名稱
                exercise_duration=exercise_duration,  # 運動持續時間
                calories_burned=calories_burned  # 消耗卡路里
            )
            print(f"已將運動數據存入資料庫: {exercise_name}, 持續 {exercise_duration} 分鐘, 消耗 {calories_burned} 卡路里")
        except Exception as e:
            print(f"存入資料庫失敗：{e}")