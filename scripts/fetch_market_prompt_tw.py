import os
import json
from utils_grok import ask_grok

PROMPT_FILE = "prompt/tw_market_data.txt"
OUTPUT_JSON = "docs/podcast/market_data_tw.json"

def fetch_market_data_from_grok():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt = f.read()

    response = ask_grok(prompt)
    try:
        data = json.loads(response)
        with open(OUTPUT_JSON, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
        print("✅ 已儲存 market_data_tw.json")
    except Exception as e:
        print("❌ Grok 回傳內容無法解析為 JSON：", e)
        print(response)

if __name__ == "__main__":
    fetch_market_data_from_grok()
