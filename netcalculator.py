from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from access_db import Userdata

class NETCalorieCalculator:
    def __init__(self, user_id):
        self.user_id = user_id
        self.user_data = None
        self.height = None
        self.weight = None
        self.gender = None
        self.duration_minutes = None
        self.distance = None

    def get_user_data(self):
        user = Userdata(self.user_id)
        self.user_data = user.search_data("u_id", self.user_id)

        if self.user_data:
            self.height = self.user_data[5]
            self.weight = self.user_data[4]
            self.gender = self.user_data[2]
            return True
        else:
            print(f"使用者 {self.user_id} 不存在")
            return False

    def set_exercise_info(self, duration_minutes, distance=None):
        self.duration_minutes = duration_minutes
        self.distance = distance

    def fetch_calories_from_website(self, exercise_id, exercise_name):
        try:
            service = Service(r"chromedriver.exe")
            driver = webdriver.Chrome(service=service)
        except WebDriverException as e:
            print("無法啟動 WebDriver，請檢查 chromedriver.exe 是否存在且版本匹配。")
            print(e)
            return None

        driver.get("https://met.0123456789.tw/")

        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "yourh"))
            )

            # 打印調試資訊
            print(f"輸入的身高：{self.height}")
            print(f"輸入的體重：{self.weight}")
            print(f"輸入的運動時間：{self.duration_minutes}")
            print(f"使用的 exercise_id：{exercise_id}")

            driver.find_element(By.ID, "yourh").send_keys(str(self.height))
            driver.find_element(By.ID, "yourw").send_keys(str(self.weight))
            driver.find_element(By.ID, "yourtime").send_keys(str(self.duration_minutes))
            driver.find_element(By.CLASS_NAME, "formc2").click()

            result = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.NAME, exercise_id))
            ).get_attribute('value')

            driver.quit()
            return result
        except TimeoutException as e:
            print("等待元素出現時超時，請檢查元素定位方式或增加等待時間。")
            print(e)
            driver.quit()
            return None
