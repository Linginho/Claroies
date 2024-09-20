import re
from openai import AzureOpenAI
from configparser import ConfigParser

config = ConfigParser()
config.read("config.ini")
client = AzureOpenAI(
    api_key=config["AzureOpenAI"]["API_KEY"],
    api_version=config["AzureOpenAI"]["API_VERSION"],
    azure_endpoint=config["AzureOpenAI"]["API_BASE"],
)

def get_chinese_str(string):
    if string :
        pre = re.compile(u'[\u4e00-\u9fa5]')
        res = re.findall(pre, string)
        res1=''.join(res)
        return res1
    else:
        return None

def intent_recognization(user_input):
    ### 設置prompt ###
    message_text = [
        {
            "role": "system",
            "content": "",
        },
        {   "role": "user", 
            "content": user_input},
    ]
    intent_types = ["運動建議", "記錄飲食", "記錄運動"]
    ### 系統設定 ###
    message_text[0]["content"] += f"""
        你會根據輸入來判斷行為類型。
        行為類型含: {intent_types[0]}、{intent_types[1]}、{intent_types[2]}。
        如果提到食物，應返回{intent_types[1]}；
        如果提到運動，應返回{intent_types[2]}。
        例如：'我今天吃了一碗拉麵' 應返回{intent_types[1]}。 
        """
    message_text[0]["content"] += "請一律用繁體中文回答。"
    ### 調用OpenAI ###
    completion = client.chat.completions.create(    
        model=config["AzureOpenAI"]["DEPLOYMENT_NAME_GPT4o"],
        messages=message_text,
        # functions=functions,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    # print(completion)
    completion_message = completion.choices[0].message # 含: function name, 意圖辨識結果
    completion_content = get_chinese_str(completion_message.content) 
    # print(completion_message)
    if completion_content in intent_types:
        result_intent = completion_content
    else:
        result_intent = '無法辨識意圖'
    return result_intent