import os
import requests
import json
from datetime import datetime
from fetch_market_data import (
    get_stock_index_data,
    get_etf_data,
    get_bitcoin_price,
    get_gold_price,
    get_dxy_index,
    get_yield_10y
)

api_key = os.getenv("MOONSHOT_API_KEY")
if not api_key:
    raise ValueError("請設定環境變數 MOONSHOT_API_KEY")

today = datetime.utcnow().strftime("%Y%m%d")
output_dir = f"docs/podcast/{today}"
os.makedirs(output_dir, exist_ok=True)
output_path = f"{output_dir}/script.txt"

# 擷取行情資料
stock_summary = "\n".join(get_stock_index_data())
etf_summary = "\n".join(get_etf_data())
bitcoin = get_bitcoin_price()
gold = get_gold_price()
dxy = get_dxy_index()
yield10y = get_yield_10y()

market_data = f"""
【今日美股指數概況】
{stock_summary}

【ETF 概況】
{etf_summary}

【其他市場指標】
{bitcoin}
{gold}
{yield10y}
{dxy}
""".strip()

# 設計繁體 prompt 結合資料
prompt = f"""
你是一位專業財經科技主持人-幫幫忙，請用繁體中文撰寫一段約10 分鐘 Podcast 播報逐字稿，語氣自然、專業、台灣專業投資人的口吻。

請以以下行情資訊為基礎，加入簡要評論與延伸深入內容：

{market_data}

並補充：
1. 美股指數：加入具體影響因素（如 Fed 政策或企業財報）
2. ETF：分析 QQQ/SPY/IBIT 的趨勢。
3. 最熱門美股五家公司最新報價、分析trend可能走向與整體資金流向概況
4. 深入探討二則最熱門 AI 工具、新創公司或 AI相關投資機會及研究報告
5. 最後以一句投資鼓勵語或金句結尾

注意事項：
- 內容需使用繁體中文撰寫
- 內容需符合一般人聽得懂的自然語氣,使用台灣慣用語，語調高低不一，語速快慢不一
- 公司與金融名詞直接用英文播報，例如 Nvidia、Fed 等
- 全文控制在約 6200～8800 字
- 僅輸出逐字稿正文，勿補充任何說明
"""

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

if response.status_code == 200:
    result = response.json()
    script_text = result["choices"][0]["message"]["content"].strip()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script_text)
    print("✅ 成功產生 Podcast 逐字稿：", output_path)
else:
    print("❌ 發生錯誤：", response.status_code, response.text)
    raise RuntimeError("Kimi API 回傳錯誤")
