import os
import json
import requests
from datetime import datetime
import pytz

TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ).strftime("%Y%m%d")

GROK_API_URL = os.getenv("GROK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")

PROMPT_FILE = "tw_market_data.txt"
OUTPUT_FILE = f"docs/podcast/{TODAY}_tw/market_data_tw.json"


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

    resp = requests.post(GROK_API_URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["text"]


def save_json(content: str):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Grok 回傳的內容不是有效 JSON 格式！")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存 market_data_tw.json 至 {OUTPUT_FILE}")


if __name__ == "__main__":
    prompt = load_prompt()
    print("🤖 正在詢問 Grok 取得市場資料...")
    content = ask_grok(prompt)
    save_json(content)