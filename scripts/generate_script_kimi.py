import os
import datetime
import requests
from fetch_market_data import (
    get_stock_index_data,
    get_etf_data,
    get_bitcoin_price,
    get_gold_price,
    get_dxy_index,
    get_yield_10y
)

# API key 設定
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

today = datetime.datetime.utcnow().strftime("%Y%m%d")
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

# 建立 prompt
prompt = f"""
你是一位專業財經科技主持人-幫幫忙，請用繁體中文撰寫一段約10 分鐘 Podcast 播報逐字稿，語氣自然、專業投資人的口吻。

請以以下行情資訊為基礎，加入簡要評論與延伸深入內容：

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
- 全文控制在約 2200～5800 字
- 僅輸出繁體中文逐字稿正文，勿輸出任何說明或 JSON，僅逐字稿正文
"""

# 優先使用 Grok，失敗時 fallback 到 Kimi
def try_grok():
    if not GROK_API_KEY:
        return None
    try:
        grok_resp = requests.post(
            url="https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mixtral-8x7b-32768",
                "messages": [
                    {"role": "system", "content": "你是專業 Podcast 撰稿助手"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            },
            timeout=60
        )
        if grok_resp.status_code == 200:
            return grok_resp.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"⚠️ Grok 回傳錯誤：{grok_resp.status_code} {grok_resp.text}")
    except Exception as e:
        print(f"⚠️ Grok 發生錯誤：{e}")
    return None

def try_kimi():
    if not MOONSHOT_API_KEY:
        raise ValueError("請設定環境變數 MOONSHOT_API_KEY")
    kimi_resp = requests.post(
        url="https://api.moonshot.cn/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {MOONSHOT_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "moonshot-v1-128k",
            "messages": [
                {"role": "system", "content": "你是專業 Podcast 撰稿助手"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95
        },
        timeout=60
    )
    if kimi_resp.status_code == 200:
        return kimi_resp.json()["choices"][0]["message"]["content"].strip()
    else:
        raise RuntimeError(f"Kimi API 回傳錯誤：{kimi_resp.status_code} {kimi_resp.text}")

# 嘗試產出逐字稿
generated = try_grok() or try_kimi()
if not generated:
    raise RuntimeError("❌ Grok 與 Kimi 都無法產出逐字稿")

# 寫入逐字稿文字檔
with open(output_path, "w", encoding="utf-8") as f:
    f.write(generated)

print("✅ 成功產生 Podcast 逐字稿：", output_path)