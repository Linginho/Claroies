# calorie_calculator.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from access_db import Userdata, Dailydata

class NETCalorieCalculator:
    def __init__(self, user_id):
        self.user_id = user_id
        self.user_data = None
        self.height = None
        self.weight = None
        self.age = None
        self.duration_minutes = None
        
    # 從資料庫獲取使用者基本資訊
    def get_user_data(self):
        user = Userdata(self.user_id)
        self.user_data = user.search_data("u_id", self.user_id)
        
        if self.user_data:
            self.height = self.user_data[5]
            self.weight = self.user_data[4]
            self.age = self.user_data[3]
        else:
            print(f"使用者 {self.user_id} 不存在")
            return False
        return True

    # 設定運動持續時間
    def set_exercise_duration(self, duration_minutes):
        self.duration_minutes = duration_minutes

    # 根據運動名稱映射ID
    def get_activity_id(self, exercise_name):
        activity_mapping = {
            '跑步': '96',
            '游泳': '127',
            '跳繩': '108',
            '單車': '30'
        }
        gender = "m" if self.user_data[2] else "w"
        
        if exercise_name in activity_mapping:
            return f"{gender}{activity_mapping[exercise_name]}"
        else:
            print("未知的運動名稱")
            return None

    # 執行卡路里計算
    def calculate_calories(self, exercise_name):
        if not self.get_user_data():
            return

        activity_id = self.get_activity_id(exercise_name)
        if not activity_id:
            return

        # 爬取網站進行卡路里計算
        service = Service(r"chromedriver.exe")
        driver = webdriver.Chrome(service=service)
        driver.get("https://met.0123456789.tw/")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "yourh"))
        )
        driver.find_element(By.ID, "yourh").send_keys(str(self.height))
        driver.find_element(By.ID, "yourw").send_keys(str(self.weight))
        driver.find_element(By.ID, "youra").send_keys(str(self.age))
        driver.find_element(By.ID, "yourtime").send_keys(str(self.duration_minutes))
        driver.find_element(By.CLASS_NAME, "formc2").click()

        result = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, activity_id))
        ).get_attribute('value')

        print(f"{exercise_name} 消耗的卡路里: {result}")
        driver.quit()

        # 保存到資料庫並返回格式化信息
        return self.save_to_db(exercise_name, result)

    # 保存運動數據到資料庫
    def save_to_db(self, exercise_name, calories_burned):
        daily_data = Dailydata(self.user_id)
        
        # 插入數據到資料庫
        daily_data.insert_data({
            "exercise_name": exercise_name,
            "duration_minutes": self.duration_minutes,
            "calories_burned": calories_burned
        })

        # 返回格式化的回覆訊息
        return f"你進行了 {exercise_name}，持續 {self.duration_minutes} 分鐘，成功消耗 {calories_burned} 卡路里，數據已記錄。"

