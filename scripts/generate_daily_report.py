#!/usr/bin/env python3
# scripts/generate_daily_report.py
import os
import datetime
import requests
import yfinance as yf
import pandas as pd
import numpy as np

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

TICKERS = ["QQQ", "0050.TW"]
START = datetime.datetime.now() - datetime.timedelta(days=365*2)
TODAY = datetime.datetime.now()

def backtest_strategy(df):
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df.dropna(inplace=True)

    df["Signal"] = np.where(df["MA5"] > df["MA20"], 1, -1)
    df["Return"] = df["Close"].pct_change()
    df["Strategy_Return"] = df["Signal"].shift(1) * df["Return"]

    # 計算交易次數與勝率（只算信號變化時）
    trade_points = df[df["Signal"].diff() != 0]
    total_trades = len(trade_points)
    win_trades = (trade_points["Strategy_Return"] > 0).sum()
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    pnl_per_trade = df["Strategy_Return"].mean() * 100
    max_drawdown = float(((df["Close"] / df["Close"].cummax() - 1).min()) * 100)

    last_signal = "BUY" if df["Signal"].iloc[-1] == 1 else "SELL"
    suggestion = "加倉" if last_signal == "BUY" else "減倉"

    return {
        "win_rate": round(float(win_rate), 2),
        "pnl_per_trade": round(float(pnl_per_trade), 2),
        "max_drawdown": round(max_drawdown, 2),
        "signal": last_signal,
        "suggestion": suggestion
    }

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
        print(f"❌ Notion 寫入失敗 ({ticker}):", res.text)
    else:
        print(f"✅ Notion 寫入成功: {ticker}")

def main():
    today_str = TODAY.strftime("%Y-%m-%d")
    for ticker in TICKERS:
        print(f"📈 回測 {ticker} 中...")
        df = yf.download(ticker, start=START.strftime("%Y-%m-%d"), end=(TODAY + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
        if df.empty:
            print(f"⚠️ {ticker} 沒有資料")
            continue

        result = backtest_strategy(df)
        print(f"{ticker} -> 信號: {result['signal']} | 勝率: {result['win_rate']}% | 平均單筆獲利: {result['pnl_per_trade']}% | 最大回撤: {result['max_drawdown']}% | 建議: {result['suggestion']}")

        write_to_notion(
            date=today_str,
            ticker=ticker,
            signal=result['signal'],
            winrate=result['win_rate'],
            pnl=result['pnl_per_trade'],
            drawdown=result['max_drawdown'],
            suggestion=result['suggestion']
        )

if __name__ == "__main__":
    main()
