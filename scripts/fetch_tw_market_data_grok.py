# scripts/fetch_tw_market_data_grok.py
import json
from xai_sdk import GrokSession

def fetch_tw_market_data():
    with open("tw_market_data.txt", "r", encoding="utf-8") as f:
        prompt = f.read()

    session = GrokSession()
    result = session.ask(prompt)

    try:
        json_start = result.find("{")
        json_str = result[json_start:]
        data = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"❌ Grok 回傳格式錯誤: {e}")

    # 儲存 JSON
    with open("market_data_tw.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ 已儲存 market_data_tw.json")

if __name__ == "__main__":
    fetch_tw_market_data()