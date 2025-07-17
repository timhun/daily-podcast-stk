import os
import json
from xai_sdk import Client
from xai_sdk.chat import user, system

with open('podcast/latest/market.json') as f:
    market = json.load(f)
with open('podcast/latest/news_ai.txt') as f:
    news_ai = f.read()
with open('podcast/latest/news_macro.txt') as f:
    news_macro = f.read()
with open('podcast/latest/quote.txt') as f:
    quote = f.read()

prompt = f"""
你是台灣財經 Podcast 主持人，請用自然、親切的台灣專業投資人語氣，寫一篇約 15 分鐘逐字稿，內容包含：
1. 美股四大指數 (.DJI, .IXIC, .SPX, SOX) 收盤/漲跌幅
2. QQQ、SPY、IBIT ETF 漲跌幅與簡易分析
3. 比特幣、黃金、十年美債數據/分析
4. Top 5 熱門美股及資金流向
5. 一則熱門AI新聞
6. 一則美國總經新聞
7. 投資金句結尾

所有數據如下：
美股/ETF: {market}
AI新聞: {news_ai}
總經: {news_macro}
金句: {quote}
"""

client = Client(api_key=os.getenv("XAI_API_KEY"), timeout=3600)
chat = client.chat.create(model="grok-4")
chat.append(system("你是Grok，一個高度智慧、親切有幫助的 Podcast 助理。"))
chat.append(user(prompt))
response = chat.sample()
with open('podcast/latest/script.txt', 'w') as f:
    f.write(response.content)