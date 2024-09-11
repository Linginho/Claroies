from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from access_db import Userdata, Dailydata

class NETCalorieCalculator:
    def __init__(self, user_id):
        self.user_id = user_id
        self.user_data = None
        self.height = None
        self.weight = None
        self.age = None
        self.duration_minutes = None

    # 從資料庫取得使用者基本資料
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

    # 根據運動名稱來對應運動ID
    def get_activity_id(self, exercise_name):
        # 定義運動名稱到ID的映射
        activity_mapping = {
            '跑步': '96',
            '游泳': '127',
            '跳繩': '108',
            '單車': '30'
        }
        # 根據使用者性別決定m還是w，True為男性，False為女性
        gender = "m" if self.user_data[2] else "w"
        
        if exercise_name in activity_mapping:
            return f"{gender}{activity_mapping[exercise_name]}"
        else:
            print("未知的運動名稱")
            return None

    # 執行爬取計算
    def calculate_calories(self, exercise_name):
        if not self.get_user_data():
            return

        # 根據運動名稱獲取對應的ID
        activity_id = self.get_activity_id(exercise_name)
        if not activity_id:
            return

        # 設定 ChromeDriver 路徑
        service = Service(r"chromedriver.exe")
        driver = webdriver.Chrome(service=service)

        # 打開目標網頁
        driver.get("https://met.0123456789.tw/")

        # 等待頁面加載並找到輸入框
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "yourh"))
        )

        # 輸入數據
        driver.find_element(By.ID, "yourh").send_keys(str(self.height))
        driver.find_element(By.ID, "yourw").send_keys(str(self.weight))
        driver.find_element(By.ID, "youra").send_keys(str(self.age))
        driver.find_element(By.ID, "yourtime").send_keys(str(self.duration_minutes))

        # 點擊“計算”按鈕
        driver.find_element(By.CLASS_NAME, "formc2").click()

        # 獲取對應運動的結果
        result = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, activity_id))
        ).get_attribute('value')

        print(f"{exercise_name}消耗的卡路里: {result}")

        # 關閉瀏覽器
        driver.quit()

        return result


# 示例用法
if __name__ == '__main__':
    calculator = NETCalorieCalculator("gg")
    calculator.set_exercise_duration(60)  # 主程式傳入持續時間
    calculator.calculate_calories("跑步")  # 主程式傳入運動名稱
