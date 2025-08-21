import os
import requests
import json

# === Notion 設定 ===
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB = os.getenv("NOTION_DB")

# === Slack 設定 ===
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

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
        print("❌ Notion 寫入失敗", res.text)


def push_signal_to_slack(signal_file="signal.json"):
    with open(signal_file, "r") as f:
        signal = json.load(f)

    msg = f"📈 *Daily QQQ Signal* ({signal['date']})\nSignal: *{signal['signal']}*\nClose: {signal['close']}"
    res = requests.post(SLACK_WEBHOOK, json={"text": msg})

    if res.status_code == 200:
        print("✅ 已發送到 Slack")
    else:
        print("❌ Slack 發送失敗", res.text)


def push_signal(signal_file="signal.json"):
    push_signal_to_notion(signal_file)
    push_signal_to_slack(signal_file)
