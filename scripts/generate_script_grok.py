import os
import requests
import json

def generate_script():
    with open("data.json") as f:
        market = json.load(f)

    prompt = f"""
請幫我產出一篇 Podcast 的逐字稿，語氣自然親切像台灣的專業投資人，語速約 1.3 倍，內容要涵蓋：
(1) 昨日美股四大指數 (.DJI, .IXIC, .SPX, SOX) 收盤與漲跌幅，
(2) QQQ ETF 的表現與簡要分析。
不要超過 1500 字。風格有點聊天但資訊正確。
輸入資料如下：
{json.dumps(market, ensure_ascii=False)}
"""

    response = requests.post("https://api.grok.example/generate",  # 替換為真實 API
        headers={"Authorization": f"Bearer {os.environ['GROK_API_KEY']}"},
        json={"prompt": prompt})
    text = response.json().get("text", "")
    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(text)

if __name__ == "__main__":
    generate_script()
