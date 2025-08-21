import os
import requests
import json

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB = os.getenv("NOTION_DB")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def push_signal_to_notion(signal_file="signal.json"):
    with open(signal_file, "r") as f:
        signal = json.load(f)

    data = {
        "parent": {"database_id": NOTION_DB},
        "properties": {
            "Date": {"date": {"start": signal["date"]}},
            "Signal": {"rich_text": [{"text": {"content": signal["signal"]}}]},
            "Close": {"number": signal["close"]}
        }
    }

    res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    if res.status_code == 200:
        print("✅ 已寫入 Notion")
    else:
        print("❌ 寫入失敗", res.text)
