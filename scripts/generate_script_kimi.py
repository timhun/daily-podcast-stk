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

# 取得日期與模式
now = datetime.datetime.now(datetime.timezone.utc)
today_str = now.strftime("%Y%m%d")
PODCAST_MODE = os.getenv("PODCAST_MODE", "us").lower()
output_dir = f"docs/podcast/{today_str}"
os.makedirs(output_dir, exist_ok=True)
script_path = f"{output_dir}/script.txt"

# 擷取行情資料
stock_summary = "\n".join(get_stock_index_data(mode=PODCAST_MODE))
etf_summary = "\n".join(get_etf_data(mode=PODCAST_MODE))
bitcoin = get_bitcoin_price()
gold = get_gold_price()
dxy = get_dxy_index()
yield10y = get_yield_10y()

market_data = f"""
【今日主要指數概況】
{stock_summary}

【ETF 概況】
{etf_summary}

【其他市場指標】
{bitcoin}
{gold}
{yield10y}
{dxy}
""".strip()

# 載入主題
theme_text = ""
theme_file = f"prompt/theme-{PODCAST_MODE}.txt"
if os.path.exists(theme_file):
    with open(theme_file, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if raw:
            theme_text = raw if raw[-1] in "。！？" else raw + "。"

# 載入 Prompt 主體
prompt_file = f"prompt/{PODCAST_MODE}.txt"
if not os.path.exists(prompt_file):
    raise FileNotFoundError(f"❌ 缺少 prompt 檔案：{prompt_file}")
with open(prompt_file, "r", encoding="utf-8") as f:
    prompt_template = f.read()

# 組合完整 prompt
prompt = prompt_template.format(market_data=market_data, theme=theme_text)

# Grok3
def generate_with_grok():
    try:
        print("🤖 使用 Grok3 嘗試產生逐字稿...")
        result = generate_script_from_grok(prompt)
        if result:
            print("✅ 成功使用 Grok3 產生逐字稿")
            return result
        raise Exception("Grok 回傳為空")
    except Exception as e:
        print(f"⚠️ Grok3 失敗：{e}")
        return None

# Kimi
def generate_with_kimi():
    try:
        print("🔁 改用 Kimi API...")
        api_key = os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            raise ValueError("❌ 未設定 MOONSHOT_API_KEY")

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
            print("✅ 成功使用 Kimi 產生逐字稿")
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            raise RuntimeError(f"Kimi API 錯誤：{response.status_code}, {response.text}")
    except Exception as e:
        print(f"⚠️ Kimi 失敗：{e}")
        return None

# OpenRouter
def generate_with_openrouter():
    try:
        print("📡 嘗試使用 OpenRouter GPT-4...")
        result = generate_script_from_openrouter(prompt)
        if result:
            print("✅ 成功使用 OpenRouter GPT-4")
            return result
        raise Exception("OpenRouter 回傳為空")
    except Exception as e:
        print(f"⚠️ OpenRouter 失敗：{e}")
        return None

# 主流程
script_text = generate_with_grok()
if not script_text:
    script_text = generate_with_kimi()
if not script_text:
    script_text = generate_with_openrouter()
if not script_text:
    raise RuntimeError("❌ 所有來源皆失敗")

# 儲存
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script_text)
print(f"✅ 已儲存逐字稿至：{script_path}")