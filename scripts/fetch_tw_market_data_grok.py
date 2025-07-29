import os
import json
import requests
from datetime import datetime
import pytz

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ).strftime("%Y%m%d")

# 設定檔案與 API
PROMPT_FILE = "prompt/tw_market_data.txt"
OUTPUT_FILE = f"docs/podcast/{TODAY}_tw/market_data_tw.json"

GROK_API_URL = os.getenv("GROK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")


def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"找不到 prompt 檔案：{PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def ask_grok(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "model": "gpt-4",
        "max_tokens": 2048,
    }

    response = requests.post(GROK_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["text"]


def save_json(content: str):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("❌ Grok 回傳內容不是有效的 JSON 格式！")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存 Grok 回傳資料：{OUTPUT_FILE}")


def main():
    prompt = load_prompt()
    print("🤖 向 Grok 發送請求...")
    content = ask_grok(prompt)
    save_json(content)


if __name__ == "__main__":
    main()