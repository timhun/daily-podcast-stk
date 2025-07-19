import os
import json
import datetime
from fetch_market_data import (
    get_stock_index_data,
    get_etf_data,
    get_bitcoin_price,
    get_gold_price,
    get_dxy_index,
    get_yield_10y
)
from generate_script_grok import generate_script_from_grok
import requests

# 取得今天日期
now = datetime.datetime.now(datetime.timezone.utc)
today_str = now.strftime("%Y%m%d")
output_dir = f"docs/podcast/{today_str}"
os.makedirs(output_dir, exist_ok=True)
script_path = f"{output_dir}/script.txt"

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

# 嘗試讀取主題
theme_text = ""
theme_file = "themes.txt"
if os.path.exists(theme_file):
    with open(theme_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        if lines:
            theme_text = lines[-1]

# 建立 prompt
prompt = f"""
你是一位專業財經科技主持人-幫幫忙，請用繁體中文撰寫一段約10 分鐘 Podcast 播報逐字稿，語氣自然、專業投資人的口吻。

請以以下行情資訊為基礎，加入評論與整體經濟深入內容：

{market_data}

並補充：
1. 美股指數：加入具體影響因素（如 Fed 政策或企業財報）
2. ETF：分析 QQQ/SPY/IBIT 的最新趨勢或投資報告
3. 比特幣BTC的研究分析或趨勢赹向或新聞
4. 原油與十年期美國公債利率分析與通貨膨漲的最新報告或新聞
5. 最熱門美股五家公司最新報價、分析trend可能走向與整體資金流向概況
6. 深入探討二則最熱門 AI 工具、新創公司及AI相關投資機會及研究報告
7. 最後以一句投資鼓勵語或金句結尾

{'請以以下主題切入角度撰寫：' + theme_text if theme_text else ''}

注意事項：
- 內容需使用繁體中文撰寫且皆採用過去24小時內最新資訊
- 內容需符合一般人聽得懂的用詞,使用台灣慣用語，語調高低不一，語速快慢不一
- 公司與金融名詞直接用英文播報，例如 Nvidia、Fed 等
- 全文控制在約 3000 字以上
- 僅輸出繁體中文逐字稿正文，勿輸出任何說明或 JSON，僅逐字稿正文
"""

# 嘗試先用 Grok，再 fallback 到 Kimi
def generate_with_grok():
    try:
        print("🤖 使用 Grok 嘗試產生逐字稿...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功使用 Grok 產生逐字稿")
            return result
        raise Exception("Grok 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok 失敗： {e}")
        return None

def generate_with_kimi():
    print("🔁 改用 Kimi API 產生逐字稿...")
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError("請設定環境變數 MOONSHOT_API_KEY")

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
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        print("❌ 發生錯誤：", response.status_code, response.text)
        raise RuntimeError("Kimi API 回傳錯誤")

# 主執行流程
script_text = generate_with_grok()
if not script_text:
    script_text = generate_with_kimi()

# 儲存逐字稿
os.makedirs(output_dir, exist_ok=True)
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script_text)

# ✅ 檢查儲存是否成功
if os.path.exists(script_path):
    print(f"✅ 已儲存逐字稿至：{script_path}")
else:
    print(f"❌ 儲存失敗：{script_path} 不存在")
