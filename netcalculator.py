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

    # 執行爬取計算
    def calculate_calories(self):
        if not self.get_user_data():
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
        driver.find_element(By.ID, "yourh").send_keys(str(self.height))  # 輸入身高
        driver.find_element(By.ID, "yourw").send_keys(str(self.weight))  # 輸入體重
        driver.find_element(By.ID, "youra").send_keys(str(self.age))  # 輸入年齡
        driver.find_element(By.ID, "yourtime").send_keys(str(self.duration_minutes))  # 輸入持續時間

        # 點擊“計算”按鈕
        driver.find_element(By.CLASS_NAME, "formc2").click()

        # 等待並獲取結果
        result = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "m089"))
        )

        calories = result.get_attribute('value')
        print(f"計算結果: {calories}")

        # 關閉瀏覽器
        driver.quit()

        # 將結果存入 Dailydata 表
        dailydata = Dailydata(self.user_id)
        dailydata.add_data(u_id=self.user_id, data_time=str(datetime.now()), food_name="爬取計算", 
                           food_calories=float(calories), exercise_name="爬取計算", exercise_duration=self.duration_minutes)
        
        return calories

# 示例用法，主程式可以像這樣使用此類別
if __name__ == '__main__':
    calculator = NETCalorieCalculator("gg")
    calculator.set_exercise_duration(60)  # 主程式傳入持續時間
    calculator.calculate_calories()
