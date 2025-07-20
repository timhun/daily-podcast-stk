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
from generate_script_openrouter import generate_script_from_openrouter
import requests

PODCAST_MODE = os.getenv("PODCAST_MODE", "us")
now = datetime.datetime.now(datetime.timezone.utc)
today_str = now.strftime("%Y%m%d")
output_dir = f"docs/podcast/{today_str}/{PODCAST_MODE}"
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

# 主題
theme_text = ""
theme_file = "themes.txt"
if os.path.exists(theme_file):
    with open(theme_file, "r", encoding="utf-8") as f:
        lines = [line.strip().strip('，。！') for line in f if line.strip()]
        if lines:
            theme_text = lines[-1]

# Prompt 載入（根據模式）
prompt_file = f"prompt/{PODCAST_MODE}.txt"
if not os.path.exists(prompt_file):
    raise FileNotFoundError(f"找不到 prompt 模板：{prompt_file}")

with open(prompt_file, "r", encoding="utf-8") as f:
    prompt_template = f.read().strip()

# 建立 prompt
prompt = prompt_template.format(
    market_data=market_data,
    theme=("請以以下主題切入角度撰寫：" + theme_text if theme_text else "")
)

# Fallback 呼叫流程
def generate_with_grok():
    try:
        print("🤖 使用 Grok3 嘗試產生逐字稿...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功使用 Grok3 產生逐字稿")
            return result
        raise Exception("Grok3 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok3 失敗：{e}")
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
        return None

def generate_with_openrouter():
    print("🔁 最後使用 OpenRouter 嘗試產生逐字稿...")
    return generate_script_from_openrouter(prompt)

# 主流程
script_text = generate_with_grok() or generate_with_kimi() or generate_with_openrouter()

# 儲存逐字稿
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script_text)
print(f"✅ 已儲存逐字稿至：{script_path}")