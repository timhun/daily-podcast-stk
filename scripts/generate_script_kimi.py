import os
import json
import requests

# ========== 讀取資料 ==========
os.makedirs('podcast/latest', exist_ok=True)

with open('podcast/latest/market.json') as f:
    market = json.load(f)
with open('podcast/latest/news_ai.txt') as f:
    news_ai = f.read()
with open('podcast/latest/news_macro.txt') as f:
    news_macro = f.read()
with open('podcast/latest/quote.txt') as f:
    quote = f.read()

# ========== 提示詞建構 ==========
prompt = f"""
你是一位 Podcast 節目編輯，要幫我撰寫一份 15 分鐘節目逐字稿，主題是「幫幫忙說財經科技投資」，口吻像專業投資人，講話自然、親切、有點幽默，台灣慣用語。

內容包括：
1. 美股四大指數收盤：.DJI {market['.DJI']['close']}（{market['.DJI']['change']}%）、.IXIC {market['.IXIC']['close']}、.SPX {market['.SPX']['close']}、SOX {market['SOX']['close']}。
2. ETF：QQQ {market['QQQ']['close']}（{market['QQQ']['change']}%）、SPY、IBIT。
3. 比特幣：{market['BTC']['close']} 美元、黃金：{market['Gold']['close']} 美元、十年美債殖利率：{market['US10Y']['close']}%。
4. 熱門美股：{'、'.join(market['Top5'])}
5. AI 新聞：{news_ai}
6. 總經新聞：{news_macro}
7. 投資金句：{quote}

請生成一段自然口語、方便語音播報的逐字稿，像廣播節目，不要條列式。
"""

# ========== 呼叫 Kimi API ==========
api_key = os.getenv("MOONSHOT_API_KEY")
if not api_key:
    raise ValueError("請設定環境變數 MOONSHOT_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "moonshot-v1-128k",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.7
}
response = requests.post("https://api.moonshot.cn/v1/chat/completions", headers=headers, json=payload)
response.raise_for_status()

text = response.json()['choices'][0]['message']['content']

# ========== 輸出 ==========
with open('podcast/latest/script.txt', 'w') as f:
    f.write(text)

print("✅ Kimi 已生成逐字稿")
