import os
import json
from datetime import datetime
import pytz

from grok_api import ask_grok_json

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ).strftime("%Y%m%d")

# 檔案路徑
PROMPT_FILE = "prompt/tw_market_data.txt"
OUTPUT_FILE = f"docs/podcast/{TODAY}_tw/market_data_tw.json"


def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"❌ 找不到 prompt 檔案：{PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def save_json_to_file(data: dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存市場資料 JSON 至 {OUTPUT_FILE}")


def main():
    user_prompt = load_prompt()
    print("📤 傳送 prompt 給 Grok：\n", user_prompt[:200], "...\n")

    market_data = ask_grok_json(user_prompt)
    save_json_to_file(market_data)


if __name__ == "__main__":
    main()