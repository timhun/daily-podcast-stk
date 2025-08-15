#!/usr/bin/env python3
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ===== 抓取 Yahoo Finance Hourly 資料 =====
def fetch_hourly_data(symbol):
    end = datetime.now()
    start = end - timedelta(days=7)  # 最近一週
    print(f"[INFO] Fetching hourly data for {symbol} from {start} to {end}")
    df = yf.download(symbol, start=start, end=end, interval="60m")
    if df.empty:
        print("[WARNING] No hourly data fetched!")
    return df

def save_hourly_csv(df, filename="reports/hourly.csv"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(filename)
    print(f"[INFO] Hourly data saved to {filename}, rows: {len(df)}")

# ===== 主流程 =====
def main():
    mode = os.environ.get("MODE", "hourly")  # 預設 hourly
    symbol = os.environ.get("SYMBOL", "0050.TW")

    print(f"[INFO] Running in MODE={mode}")
    if mode == "hourly":
        df = fetch_hourly_data(symbol)
        save_hourly_csv(df)

    # ===== 這裡可放原本的 weekly/daily 處理邏輯 =====
    if mode == "weekly":
        print("[INFO] Weekly mode logic not implemented yet.")
    elif mode == "daily":
        print("[INFO] Daily mode logic not implemented yet.")

    print("[INFO] run_pipeline.py finished.")

if __name__ == "__main__":
    main()