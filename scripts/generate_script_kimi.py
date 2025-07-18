import os
import requests
import json
from datetime import datetime, timezone

# 讀取環境變數
api_key = os.getenv("MOONSHOT_API_KEY")
if not api_key:
    raise ValueError("請設定環境變數 MOONSHOT_API_KEY")

# 取得今天日期（UTC 時區）
today = datetime.now(timezone.utc).strftime("%Y%m%d")
output_dir = f"docs/podcast/{today}"
os.makedirs(output_dir, exist_ok=True)
output_path = f"{output_dir}/script.txt"

# 撰寫 prompt（已經是繁體中文）
prompt = """你是一位專業財經科技主持人-幫幫忙，請用繁體中文撰寫一段每日 Podcast 播報逐字稿，語氣自然、親切、台灣專業投資人的口吻。

內容請包含：
1. 今日美股四大指數（道瓊、NASDAQ、S&P500、費半）收盤與漲跌幅
2. QQQ、SPY、IBIT ETF 變化簡評
3. 比特幣、黃金、十年期美債殖利率簡析
4. 熱門美股與資金流向概況
5. 一則熱門 AI 工具、公司或 AI 投資機會（資訊來源儘可能來自 Bloomberg、Google Finance、Yahoo Finance 或富途牛牛）
6. 最後加一句投資鼓勵語或金句，溫暖收尾

注意事項：
- 請使用繁體中文撰寫
- 所有數據需兩個資料源交叉比對以確保正確性
- 語氣口語自然，具生活感；公司與金融用語直接用英文
- 長度建議 7分鐘
- 僅輸出逐字稿正文，請勿包含 JSON、系統提示或多餘格式說明
"""

# 呼叫 Kimi API
response = requests.post(
    url="https://api.moonshot.cn/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "moonshot-v1-128k",
        "messages": [
            {"role": "system", "content": "你是專業的 Podcast 撰稿助手"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.95
    }
)

# 儲存回應
if response.status_code == 200:
    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ 成功產生 Podcast 逐字稿")
    print("📄 儲存於：", output_path)
else:
    print("❌ 發生錯誤：", response.status_code, response.text)
    raise RuntimeError("Kimi API 回傳錯誤")
