from flask import Flask, request, abort, render_template, redirect, url_for, jsonify , send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage,FlexSendMessage,
    ButtonsTemplate, PostbackAction, ImageMessage,
    QuickReply, QuickReplyButton, MessageAction, URIAction, PostbackEvent
)
import requests
from configparser import ConfigParser
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
import io
import base64
from PIL import Image
import threading
import time
import sqlite3
from datetime import datetime
from access_db import Userdata, Dailydata  # 資料庫操作
from health_dashboard import HealthDashboard  # 健康數據監控
from food_analyzer import FoodCalorieAnalyzer  # 食物熱量分析
import atexit
from sport_caculate import CalorieAnalyzer
from intent_recog import intent_recognization  # Intent Recognition
from food_analyzer import FoodCalorieAnalyzer  # Food Analyzer
from openai import AzureOpenAI
import os

class Lineca:
    def __init__(self):
        self.app = Flask(__name__)
        self.config = ConfigParser()
        self.config.read("config.ini")
        self.channel_access_token = self.config["LineBot"]["CHANNEL_ACCESS_TOKEN"]
        self.channel_secret = self.config["LineBot"]["CHANNEL_SECRET"]
        self.flask_host = self.config["Flask"]["HOST"]
        self.flask_port = int(self.config["Flask"]["PORT"])
        self.line_bot_api = LineBotApi(self.channel_access_token)
        self.handler = WebhookHandler(self.channel_secret)
        
     

        # 初始化 Google Generative AI
        self.llm_gemini = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=self.config["Gemini"]["API_KEY"],
            convert_system_message_to_human=True,
        )

        # 初始化健康儀表板
        self.dashboard = HealthDashboard(self.app)

        # 設置 Rich Menu IDs
        self.rich_menu_ids = [
            "richmenu-4232b0e308a3e8e44dc8e3105b14eeda",  # Rich Menu 1
            "richmenu-33bbcb678f351f81fcab231cd8482f16",  # Rich Menu 2
            "richmenu-36ec35e9b2bd50d762f766ee7acb45ee",  # Rich Menu 3
            "richmenu-7875ecdd8cb110f2eb4f679fa67c78db",  # Rich Menu 4
            "richmenu-436cf2f0a5002f90ddee110edc4361e5",  # Rich Menu 5
            "richmenu-62aedc31db3e237e11734fa4424761e5",  # Rich Menu 6
            "richmenu-e4a7b1edbf925d55ae99a9fe5ee02783",  # Rich Menu 7
            "richmenu-aec27372b1a79757b25ce21d046ae1ce"   # Rich Menu 8
        ]

        self.user_states = {}
        self.monitoring_users = {}
        self.monitor_intervals = {
            "daily": 86400,  # 每天
            "hourly": 3600,  # 每小時
            "custom": None   # 用戶自定義（需要指定時間）
        }
        self.user_target_weights = {}

        # 初始化日誌
        logging.basicConfig(level=logging.INFO)

        # 設置路由和處理函數
        self.setup_routes()
    def close_databases(self):
        """關閉資料庫連接"""
        if self.user_db:
            self.user_db.close_db()
        if self.daily_db:
            self.daily_db.close_db()

    def setup_routes(self):

        # 設定 /callback 路由
        @self.app.route("/callback", methods=['POST'])
        def callback():
            signature = request.headers['X-Line-Signature']
            body = request.get_data(as_text=True)

            logging.info(f"Request body: {body}")

            try:
                self.handler.handle(body, signature)
            except InvalidSignatureError:
                logging.error("Invalid signature. Check your channel secret and access token.")
                abort(400)
                return 'OK'


        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(os.path.join(self.app.root_path, 'static'),
                                    'favicon.ico', mimetype='image/vnd.microsoft.icon')
        # 設置運動數據儀表板的路由
        @self.app.route("/dashboard/<user_id>")
        def display_dashboard(user_id):
            # 傳入 user_id 動態生成健康儀表板
            return redirect(f"/dashboard/?user_id={user_id}")

        @self.app.route("/form", methods=['GET', 'POST'])
        def form():
            if request.method == 'POST':
                # 從 JSON 資料中提取字段
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': '無效的資料格式。'}), 400

                u_id = data.get('u_id')
                name = data.get('name')
                gender = data.get('gender')
                age = data.get('age')
                height = data.get('height')
                weight = data.get('weight')
                activity_level = data.get('activity_level', 1.2)  # 默認值

                # 確認 u_id 是否被正確接收
                logging.info(f"接收到的 u_id: {u_id}")
                logging.info(f"接收到的資料 - 姓名: {name}, 年齡: {age}, 身高: {height}, 體重: {weight}, 性別: {gender}, 活動水平: {activity_level}")

                # 檢查必要的字段
                if not all([u_id, name, gender, age, height, weight]):
                    return jsonify({'status': 'error', 'message': '請填寫所有必填欄位。'}), 400

                # 將資料存入資料庫
                try:
                    user_data = Userdata(u_id)
                    # 這裡根據你的資料庫方法調用 add_data，移除 u_id 參數
                    user_data.add_data(name, gender, age, weight, height, activity_level)
                except Exception as e:
                    logging.error(f"資料庫操作失敗: {e}")
                    return jsonify({'status': 'error', 'message': '資料庫操作失敗。'}), 500

                # 返回成功響應
                return jsonify({'status': 'success', 'message': '資料已成功提交！'}), 200

            else:  # GET 方法以呈現表單
                u_id = request.args.get('u_id')
                logging.info(f"訪問表單的 u_id: {u_id}")

                if not u_id:
                    return "無效的用戶 ID。", 400

                # 從資料庫中檢索用戶資料
                user_data = Userdata(u_id)
                user_record = user_data.search_data('u_id', u_id)
                if user_record:
                    # 將使用者記錄轉換為字典
                    column_names = user_data.get_all_columns()
                    user_dict = dict(zip(column_names, user_record))
                else:
                    # 如果使用者不存在，顯示空白表單讓用戶填寫資料
                    logging.info("使用者不存在，顯示空白表單讓用戶填寫資料")
                    user_dict = {}  # 顯示空白表單

                return render_template('user_form.html', u_id=u_id, user_dict=user_dict)      

        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_message(event):
            user_id = event.source.user_id  # 獲取用戶的 user_id
            user_message = event.message.text.strip()
            reply_token = event.reply_token
            self.user_db = Userdata(user_id)  # 傳入 user_id
            self.daily_db = Dailydata(user_id)  # 傳入 user_id

            # 確保用戶狀態存在
            self.ensure_user_state(user_id)

            # 確認當前用戶狀態
            current_state = self.user_states.get(user_id, {}).get('state', None)

            # Step 1: 檢查用戶是否輸入類似 "60公斤" 並進行減肥計畫處理
            if current_state == 'awaiting_target_weight':
                # 移除可能的「公斤」單位，然後檢查是否為數字
                cleaned_message = user_message.replace('公斤', '').strip()
                if cleaned_message.replace('.', '', 1).isdigit():
                    # 處理目標體重的邏輯
                    target_weight = float(cleaned_message)
                    self.user_states[user_id]['state'] = 'target_weight_set'  # 更新狀態
                    self.user_target_weights[user_id] = target_weight  # 保存目標體重

                    # 生成並回覆個人化減肥計畫
                    user_data = self.get_user_data(user_id)
                    if user_data:
                        diet_plan, standards = self.get_personalized_plan(user_data, target_weight)
                        self.line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=f'您的減肥建議：\n{diet_plan}')
                        )
                    # 保存標準到用戶狀態
                    self.user_states[user_id]['standards'] = standards

                    # 根據標準切換 Rich Menu 或觸發其他功能
                    self.switch_rich_menu(user_id, standards)

                    # 通知用戶監控已啟動
                    self.line_bot_api.push_message(user_id, TextSendMessage(text="我們已開始監控您的健康數據，會定期提醒您！"))
                    self.start_monitoring(user_id)
                    return  # 避免進入後續的意圖辨識邏輯
                
            # Step 1.2: 觸發“我的計畫”
            if user_message == "我的計畫":
                user_data = self.get_user_data(user_id)
                if not user_data:
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='請先更新您的基本資料, 才能生成您的個人化減肥計畫')
                    )
                    return
                if 'target_weight' not in user_data:
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='請告訴我您的目標體重（公斤）：')
                    )
                    self.user_states[user_id]['state'] = 'awaiting_target_weight'
                return  # 返回，避免進入其他處理邏輯

            # Step 2: 觸發客服小幫手對話
            if user_message == "呼叫小幫手" or user_message == "客服" or user_message == "help" or user_message == "幫助": 
                self.user_states[user_id]['in_gemini_chat'] = True  # 開始 Gemini 對話
                self.line_bot_api.reply_message(reply_token, TextSendMessage(text="已進入客服小幫手對話，請輸入問題。"))
                return  # 返回，避免進入其他處理邏輯
            

            # Step 3: 結束客服小幫手對話
            elif user_message == "結束對話" or user_message == "退出"or user_message == "bye" or user_message == "掰掰":
                self.user_states[user_id]['in_gemini_chat'] = False  # 結束 Gemini 對話
                self.line_bot_api.reply_message(reply_token, TextSendMessage(text="已退出客服小幫手對話。"))
                return  # 返回，避免進入其他處理邏輯

            # Step 4: 檢查用戶是否處於 Gemini 對話模式
            if self.user_states.get(user_id, {}).get('in_gemini_chat', False):
                try:
                    logging.info(f"Gemini對話模式中: {user_message}")
                    human_message = HumanMessage(content=user_message)
                    result = self.llm_gemini.invoke([human_message])
                    response_text = result.content.strip()
                    self.line_bot_api.reply_message(reply_token, TextSendMessage(text=response_text))
                except LineBotApiError as e:
                    logging.error(f"Error occurred: {e.message}")
                    self.line_bot_api.reply_message(reply_token, TextSendMessage(text='處理您的請求時發生錯誤，請稍後再試。'))
                return  # 返回，避免進入其他處理邏輯

            # Step 5: 預定義消息處理邏輯
            predefined_commands = ['運動建議', '更新資料', '我的計畫','我完成任務', '我沒有完成任務']
            if user_message in predefined_commands:
                logging.info(f"處理預定義命令: {user_message}")
                self.process_text_message(event, user_id)  # 預定義命令處理邏輯
                return  # 完成處理後直接返回，避免進一步處理
            



            # 處理「記錄飲食」按鈕-意圖識別
            if user_message == '記錄飲食':
                logging.info("Processing: 記錄飲食與運動")
                self.user_states[user_id]['state'] = 'awaiting_food_or_exercise'
                self.line_bot_api.reply_message(reply_token, TextSendMessage(text="請輸入您的飲食或運動資訊："))
                return

            if current_state == 'awaiting_food_or_exercise':
                logging.info("Processing user input for food or exercise")
                # 使用 IntentRecognition 處理使用者輸入
                intent =intent_recognization (user_message) 
                try:
                    if intent == "記錄運動":
                        # 處理運動輸入
                        calorie_analyzer = CalorieAnalyzer(user_id)
                        # 將提取的資訊傳遞給 CalorieAnalyzer
                        result_message = calorie_analyzer.handle_user_input(user_message) #這裡返回的是一個字串
                        self.line_bot_api.reply_message(reply_token, TextSendMessage(text=result_message))
                    elif intent == "記錄飲食":
                        food_analyzer = FoodCalorieAnalyzer(user_id)
                        result_message = food_analyzer.analyze_and_store_food_calories(user_message)
                        self.line_bot_api.reply_message(reply_token, TextSendMessage(text=result_message))
                    else:
                        # 無法識別的意圖
                        self.line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，我無法識別您的輸入，請嘗試描述您的飲食或運動。"))

                    # 重置使用者狀態
                    self.user_states[user_id]['state'] = None
                    return
                
                except Exception as e:
                    logging.error(f"處理輸入發生錯誤: {e}")
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text="處理請求發生錯誤，稍後再試。")
                    )
                    return     
            logging.info("未觸發意圖識別或Gemini對話，無需回覆")


       

        # 處理 ImageMessage
        @self.handler.add(MessageEvent, message=ImageMessage)
        def handle_image_message(event):
            self.process_image_message(event)

        # 處理 PostbackEvent
        @self.handler.add(PostbackEvent)
        def handle_postback(event):
            self.process_postback(event)
  
    def start(self):
        self.app.run(host=self.flask_host, port=self.flask_port, debug=True)

    def get_user_data(self, user_id):
        """從資料庫中獲取用戶的基本資料"""
        user_record = self.user_db.search_data('u_id', user_id)
        if user_record:
            return user_record  # 直接返回搜索到的用戶資料
        else:
            return None

    def process_text_message(self, event, user_id):
        try:
            user_message = event.message.text
            reply_token = event.reply_token
            logging.info(f"Received message: {user_message}, Reply Token: {reply_token}")

            if user_message == '運動建議':
                quick_reply_buttons = QuickReply(
                    items=[
                        QuickReplyButton(action=MessageAction(label="跑步", text="我選擇了跑步")),
                        QuickReplyButton(action=MessageAction(label="游泳", text="我選擇了游泳")),
                        QuickReplyButton(action=MessageAction(label="騎自行車", text="我選擇了騎自行車")),
                        QuickReplyButton(action=MessageAction(label="跳繩", text="我選擇了跳繩"))
                    ]
                )
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(
                        text="請選擇一個運動方式:",
                        quick_reply=quick_reply_buttons
                    )
                )
            elif user_message == '更新資料':
                logging.info("Processing: 更新資料")
                # 生成帶有 u_id 的表單 URL
                form_url = url_for('form', _external=True) + f"?u_id={user_id}"
                template_message = TemplateSendMessage(
                    alt_text='查看選項',
                    template=ButtonsTemplate(
                        title='查看資料',
                        text='請選擇項目',
                        actions=[
                            PostbackAction(label='團隊介紹', data='action=team_introduction'),
                            URIAction(label='更新基本資料', uri=form_url),
                            PostbackAction(label='運動數據', data='action=exercise_data'),
                            MessageAction(label='運動建議', text='運動建議')  # 此處可發送「運動建議」
                        ]
                    )
                )
                self.line_bot_api.reply_message(reply_token, template_message)
            elif user_message == '我的計畫':
                logging.info("Processing: 我的計畫")
                user_data = self.get_user_data(user_id)
                if not user_data:
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='請先更新您的基本資料, 才能生成您的個人化減肥計畫')
                    )
                    return
                if 'target_weight' not in user_data:
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='請先設置您的目標體重，才能生成個人化的減肥計畫')
                    )
                    return

                self.line_bot_api.reply_message(reply_token, TextSendMessage(text="請告訴我您的目標體重（公斤）："))
                self.user_states[user_id]['state'] = 'awaiting_target_weight'

            

            elif user_message == '我完成任務':
                logging.info("Processing: 我完成了任務")
                # 將 Rich Menu 切換回預設的第 0 張
                self.user_states[user_id]['current_rich_menu_index'] = 0
                rich_menu_id = self.rich_menu_ids[0]  # 預設為第 0 張 Rich Menu

                try:
                    # 切換 Rich Menu
                    self.line_bot_api.link_rich_menu_to_user(user_id, rich_menu_id)
                    logging.info(f"Switched Rich Menu for user {user_id} back to the default menu {rich_menu_id}")
                    
                    # 回應使用者
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='太棒了！您已完成任務！')
                    )
                except LineBotApiError as e:
                    logging.error(f"Error switching Rich Menu for user {user_id}: {e.message}")
                    self.line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text='不能回歸滿血,請稍後再試。')
                    )
                self.start_monitoring(user_id)
            elif user_message == '我沒有完成任務':
                logging.info("Processing: 我沒有完成任務")
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text='沒關係，請再接再厲！')
                )
        except LineBotApiError as e:
            logging.error(f"Error occurred: {e.message}")
            self.line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='處理您的請求時發生錯誤，請稍後再試。')
            )

 
    def process_image_message(self, event):
        try:
            reply_token = event.reply_token
            user_id = event.source.user_id
            self.user_db = Userdata(user_id)
            self.daily_db = Dailydata(user_id)
            logging.info(f"Processing image with Reply Token: {reply_token}")

            # 獲取消息的 ID
            message_id = event.message.id
            headers = {
                "Authorization": f"Bearer {self.channel_access_token}"
            }
            content_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"

            # 請求圖片內容
            response = requests.get(content_url, headers=headers)
            if response.status_code != 200:
                logging.error(f"無法下載圖片。狀態碼: {response.status_code}")
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text="圖片下載失敗，請稍後再試。")
                )
                return
            
            # 使用 PIL 轉換圖片
            image = Image.open(io.BytesIO(response.content))

            image.thumbnail((512, 512), Image.LANCZOS)

            # 將圖片轉換為 base64 格式
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # 打印圖片 base64 長度以進行調試
            logging.info(f"圖片 base64 長度: {len(img_base64)}")

            # 構建發送給 Gemini 的請求內容
            user_message = f"分析這張食物圖片，base64格式：{img_base64}"

            # 使用 Langchain 調用 Google Gemini API 進行分析
            human_message = HumanMessage(content=user_message)
            result = self.llm_gemini.invoke([human_message])

            # 解析 Gemini 回應
            response_text = result.content
            logging.info(f"Gemini 回應: {response_text}")

            # 假設 Gemini 返回的內容包含食物名稱和卡路里數值
            try:
                # 根據實際的回應解析出食物名稱和卡路里
                food_name = "解析出的食物名稱"  # 替換為實際解析內容
                calorie_intake = 200  # 替換為實際解析卡路里數值
            except (KeyError, ValueError, IndexError):
                logging.error("無法從 Gemini 回應中解析食物名稱或卡路里數值")
                food_name = "未知食物"
                calorie_intake = 0

            # 將攝取的卡路里數據存入資料庫
            data_time = datetime.now().strftime('%Y-%m-%d')
            self.daily_db.add_calorie_intake(user_id, data_time, food_name, calorie_intake)

            # 獲取當天總卡路里數據
            total_calories_food, total_calories_burned = self.daily_db.get_total_calories(user_id, data_time)

            # 檢查用戶的每日卡路里限制
            daily_limit = self.user_states.get(user_id, {}).get('daily_calorie_limit', None)

            # 如果超過限制，則提醒用戶
            if daily_limit is not None and (total_calories_food - total_calories_burned) > daily_limit:
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=f"這是 {food_name}，您本餐攝取了 {calorie_intake} 卡路里，已超過今日的熱量限制，建議進行適當的運動。")
                )
                # 切換 Rich Menu，鼓勵用戶完成運動
                self.switch_rich_menu(user_id, self.user_states[user_id]['current_rich_menu_index'] + 1)
                self.schedule_rich_menu_switch(user_id)
            else:
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=f"這是 {food_name}，您本餐攝取了 {calorie_intake} 卡路里，繼續保持！")
                )

        except Exception as e:
            logging.error(f"處理圖片時發生錯誤: {e}")
            self.line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="處理圖片時發生錯誤，請稍後再試。")
            )
        
    def create_member_bubble(self, name, role, image_url):
        # 定義 hero 部分
        hero_section = {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover"
        }

        # 定義 body 部分
        body_section = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": name,
                    "weight": "bold",
                    "size": "xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": f"負責項目: {role}",
                    "size": "md",
                    "align": "center",
                    "color": "#666666",
                    "wrap": True
                }
            ]
        }

        # 返回整個 bubble 結構
        return {
            "type": "bubble",
            "size": "giga",
            "hero": hero_section,
            "body": body_section
        }
    
    def process_postback(self, event):
        postback_data = event.postback.data
        user_id = event.source.user_id
        reply_token = event.reply_token

        if postback_data == 'action=team_introduction':
            logging.info("Processing: 團隊介紹 Postback")

            # 成員資料
            self.website_url =self.config["ngrok"]["website_url"]      #隨ngrok網址變動
            team_members = [
                {"name": "小賴", "role": "前端，系統整合", "image": f"{self.website_url}/static/images/member1.jpg"},
                {"name": "威廉", "role": "API開發", "image": f"{self.website_url}/static/images/member2.jpg"},
                {"name": "JOJO", "role": "API開發", "image": f"{self.website_url}/static/images/member3.jpg"},
                {"name": "Vicky", "role": "API開發", "image": f"{self.website_url}/static/images/member4.jpg"},
                {"name": "Steven", "role": "資料庫開發", "image": f"{self.website_url}/static/images/member5.jpg"},
                {"name": "James", "role": "資料庫開發", "image": f"{self.website_url}/static/images/member6.jpg"},
                {"name": "肥羊", "role": "耍廢", "image": f"{self.website_url}/static/images/member7.jpg"},
            ]

            # 使用函數生成所有成員的 bubbles
            bubbles = [self.create_member_bubble(member["name"], member["role"], member["image"]) for member in team_members]

            # 建立 Flex Message
            flex_message = FlexSendMessage(
                alt_text='團隊介紹',
                contents={
                    "type": "carousel",
                    "contents": bubbles
                }
            )

            # 發送 Flex Message
            self.line_bot_api.reply_message(reply_token, flex_message)
            
        elif postback_data == 'action=exercise_data':
            logging.info("Processing: 運動數據 Postback")
            # 生成用戶的健康儀表板 URL
            dashboard_url = url_for('display_dashboard', user_id=user_id, _external=True)

            # 回覆用戶，提供跳轉到健康儀表板的 URL
            self.line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=f"請前往以下網址查看您的健康數據：\n{dashboard_url}")
            )

    def switch_rich_menu(self, user_id, standards):
        """
        根據標準切換 Rich Menu，並設置定時器每隔2小時切換一次，直到最後一張。
        如果已經達到最後一張或達成目標，則停止切換。

        參數：
        - user_id: 用戶 ID。
        - standards: 字典，包含判斷標準。
        """
        recommended_daily_calories = standards['recommended_daily_calories']
        current_rich_menu_index = self.user_states[user_id].get('current_rich_menu_index', 0)
        daily_limit = self.user_states[user_id]['daily_calorie_limit']

        # 檢查用戶是否超過每日卡路里限制，僅在超過時切換 Rich Menu
        if recommended_daily_calories > daily_limit:
            if current_rich_menu_index < len(self.rich_menu_ids) - 1:
                # 切換到下一個 Rich Menu
                current_rich_menu_index += 1
                self.user_states[user_id]['current_rich_menu_index'] = current_rich_menu_index
                rich_menu_id = self.rich_menu_ids[current_rich_menu_index]
                try:
                    self.line_bot_api.link_rich_menu_to_user(user_id, rich_menu_id)
                    logging.info(f"Switched Rich Menu for user {user_id} to {rich_menu_id}")
                except LineBotApiError as e:
                    logging.error(f"Error switching Rich Menu for user {user_id}: {e.message}")

                # 設置定時器每隔2小時切換一次
                if user_id in self.timers:
                    self.timers[user_id].cancel()
                timer = threading.Timer(7200, self.switch_rich_menu, [user_id, standards])
                self.timers[user_id] = timer
                timer.start()
            else:
                logging.info(f"User {user_id} has reached the last Rich Menu.")
        else:
            logging.info(f"User {user_id} is within the daily calorie limit. No Rich Menu switch needed.")
    
    def get_personalized_plan(self, user_data, target_weight):
        """
        根據用戶的基本資料和目標體重，計算每日建議攝取的卡路里，並生成個人化的減肥計畫。

        參數：
        - user_data: 字典，包含用戶的基本資料（年齡、身高、體重、性別等）。
        - target_weight: 浮點數，目標體重（公斤）。

        返回：
        - plan: 字串，個人化的減肥計畫建議。
        - standards: 字典，包含判斷標準。
        """
        # 從用戶資料中提取所需資訊
        age = user_data['age']
        height = user_data['height']
        weight = user_data['weight']
        gender = user_data.get('gender', 1)  # 預設為男性，1: 男性, 0: 女性

        # 計算基礎代謝率（BMR），使用 Mifflin-St Jeor 方程
        if gender == 1:
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        # 使用用戶的活動係數
        activity_level = user_data.get('activity_level', 1.375)
        daily_calories = bmr * activity_level

        # 計算需要減少的體重（公斤）
        weight_loss_needed = weight - target_weight

        # 將減肥時間範圍設為 8 到 12 週，取決於減重量
        if weight_loss_needed <= 5:
            weeks = 12 # 小於等於 5 公斤，設置 12 週計畫
        else:
            weeks = 25  # 超過 5 公斤，設置 25 週計畫

        # 計算每日熱量赤字
        total_calorie_deficit = weight_loss_needed * 7700
        daily_calorie_deficit = total_calorie_deficit / (weeks * 7)

        # 設置每日卡路里赤字的安全範圍
        if daily_calorie_deficit > 1000:
            daily_calorie_deficit = 1000  # 最大每日卡路里赤字不超過 1000
        elif daily_calorie_deficit < 500:
            daily_calorie_deficit = 500  # 最小每日卡路里赤字不低於 500

        # 計算每日建議攝取的卡路里
        recommended_daily_calories = daily_calories - daily_calorie_deficit

        # 確保每日攝取熱量不低於最低安全值（男性不低於 1500 卡，女性不低於 1200 卡）
        if gender == 1 and recommended_daily_calories < 1500:
            recommended_daily_calories = 1500
        elif gender == 0 and recommended_daily_calories < 1200:
            recommended_daily_calories = 1200

        # 將每日建議攝取熱量存入用戶狀態
        user_id = user_data['u_id']
        if self.user_states.get(user_id) is None:
            self.user_states[user_id] = {}
        self.user_states[user_id]['daily_calorie_limit'] = recommended_daily_calories

        # 修改提示詞，要求 Gemini 只生成具體的建議，並刪除額外的問題
        basic_plan = (
            f"根據您的資料，您的基礎代謝率（BMR）為 {bmr:.2f} 卡路里。\n"
            f"為了在 {weeks} 週內達到目標體重，您每日應攝取約 {recommended_daily_calories:.2f} 卡路里。\n"
            "請根據此建議進行減肥，並確保遵循健康的飲食和適當的運動。"
        )

        # 調用 Gemini，要求它不添加多餘的問題，只生成具體的減肥建議
        human_message = HumanMessage(content=f"你是一個減肥專家，請根據以下信息，生成一個簡單且具體的減肥建議，不要包括任何問題：\n{basic_plan}")
        result = self.llm_gemini.invoke([human_message])
        refined_plan = result.content.strip()

        # 生成判斷標準
        standards = {
            'bmr': bmr,
            'daily_calories': daily_calories,
            'recommended_daily_calories': recommended_daily_calories,
            'weight_loss_needed': weight_loss_needed,
            'total_calorie_deficit': total_calorie_deficit,
            'daily_calorie_deficit': daily_calorie_deficit,
            'weeks': weeks
        }

        return refined_plan, standards

    def get_current_calories(self, user_id):
        data_time = datetime.now().strftime('%Y-%m-%d')
        total_food_calories, total_calories_burned = self.daily_db.get_total_calories(user_id, data_time)
        return total_food_calories - total_calories_burned

    def start_monitoring(self, user_id):

        """
        開始監控用戶的健康數據，並根據標準切換 Rich Menu。

        參數：
        - user_id: 用戶 ID。
        """
        # 獲取用戶的標準
        standards = self.user_states.get(user_id, {}).get('standards', None)
        if not standards:
            logging.error(f"No standards found for user {user_id}")
            return

        # 檢查用戶的攝取卡路里是否超標
        daily_calorie_limit = self.user_states[user_id]['daily_calorie_limit']
        current_calories = self.get_current_calories(user_id)  # 假設有一個函數可以獲取用戶當前的攝取卡路里

        if current_calories > daily_calorie_limit:
            # 用戶攝取的卡路里超標，切換 Rich Menu
            self.switch_rich_menu(user_id, standards)
        else:
            logging.info(f"User {user_id} is within the daily calorie limit.")

    def ensure_user_state(self, user_id):
        """用戶狀態紀錄。"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'state': None,
                'in_gemini_chat': False,  # 默認為false
                'current_rich_menu_index': 0,
                'standards': {}
            }

if __name__ == "__main__":
    # 全局關閉資料庫連接
    bot_app = Lineca()
    atexit.register(bot_app.close_databases)
    bot_app.start()