import os
import json
import requests
from datetime import datetime
import pytz

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ).strftime("%Y%m%d")

PROMPT_FILE = "prompt/tw_market_data.txt"
OUTPUT_FILE = f"docs/podcast/{TODAY}_tw/market_data_tw.json"

GROK_API_URL = os.getenv("GROK_API_URL")
GROK_API_KEY = os.getenv("GROK_API_KEY")


def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"❌ 找不到 prompt 檔案：{PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def ask_grok_for_json(prompt: str) -> dict:
    if not GROK_API_URL or not GROK_API_KEY:
        raise ValueError("請設定環境變數 GROK_API_URL 與 GROK_API_KEY")

    print("📡 正在呼叫 Grok API...")

    response = requests.post(
        url=GROK_API_URL,
        headers={"Authorization": f"Bearer {GROK_API_KEY}"},
        json={"messages": [{"role": "user", "content": prompt}]}
    )
    response.raise_for_status()
    data = response.json()
    reply = data["choices"][0]["message"]["content"].strip()

    print("🔍 Grok 回傳內容（前 500 字）：\n", reply[:500])

    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        raise ValueError("❌ Grok 回傳內容不是合法的 JSON 格式")


def save_json_to_file(data: dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存 market_data 至 {OUTPUT_FILE}")


def main():
    user_prompt = load_prompt()
    market_data = ask_grok_for_json(user_prompt)
    save_json_to_file(market_data)


if __name__ == "__main__":
    main()