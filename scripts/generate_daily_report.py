#!/usr/bin/env python3
# scripts/generate_daily_report.py
import os
import requests
from datetime import datetime

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def write_to_notion(date, ticker, signal, winrate, pnl, drawdown, suggestion):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": f"{ticker} {date}"}}]},
            "Date": {"date": {"start": date}},
            "Ticker": {"rich_text": [{"text": {"content": ticker}}]},
            "Signal": {"rich_text": [{"text": {"content": signal}}]},
            "Backtest_WinRate": {"number": winrate},
            "PnL_Per_Trade": {"number": pnl},
            "Max_Drawdown": {"number": drawdown},
            "Position_Suggestion": {"rich_text": [{"text": {"content": suggestion}}]}
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print("❌ Notion 寫入失敗:", res.text)
    else:
        print("✅ Notion 寫入成功")

# 範例呼叫
if __name__ == "__main__":
    write_to_notion(
        date=datetime.now().strftime("%Y-%m-%d"),
        ticker="QQQ",
        signal="BUY",
        winrate=0.65,
        pnl=1.23,
        drawdown=-3.45,
        suggestion="加倉"
    )
