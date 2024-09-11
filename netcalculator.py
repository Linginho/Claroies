from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from access_db import Userdata, Dailydata

def netcalculator(user_id):
    # 從資料庫取得使用者資訊
    user = Userdata(user_id)
    user_data = user.search_data("u_id", user_id)
    
    # 確保使用者存在
    if not user_data:
        print(f"使用者 {user_id} 不存在")
        return
    
    height, weight, age, activity_level = user_data[5], user_data[4], user_data[3], user_data[6]

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
    driver.find_element(By.ID, "yourh").send_keys(str(height))  # 輸入身高
    driver.find_element(By.ID, "yourw").send_keys(str(weight))   # 輸入體重
    driver.find_element(By.ID, "youra").send_keys(str(age))   # 輸入年齡
    driver.find_element(By.ID, "yourtime").send_keys("60")  # 輸入持續時間（假設）

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
    dailydata = Dailydata(user_id)
    dailydata.add_data(u_id=user_id, data_time=str(datetime.now()), food_name="爬取計算", 
                       food_calories=float(calories), exercise_name="爬取計算", exercise_duration=60)
    
    return calories

# 示例用法
if __name__ == '__main__':
    netcalculator("gg")
