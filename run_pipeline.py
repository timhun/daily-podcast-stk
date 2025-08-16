#!/usr/bin/env python3
# run_pipeline.py

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ========== 設定 ==========
TICKERS = {
    "QQQ": "QQQ",
    "0050": "0050.TW"
}

REPORTS_DIR = "reports"
HOURLY_CSV_PATH = os.path.join(REPORTS_DIR, "hourly.csv")


# ========== 工具函式 ==========
def fetch_hourly_data(symbol):
    end = datetime.now()
    start = end - timedelta(days=7)
    print(f"[INFO] Fetching hourly data for {symbol} from {start} to {end}")

    try:
        df = yf.download(symbol, start=start, end=end, interval="60m")
        print(f"[DEBUG] df.shape={df.shape}")
        if not df.empty:
            print(f"[DEBUG] First few rows for {symbol}:\n{df.head(3)}")
        else:
            print(f"[WARNING] No hourly data fetched for {symbol}!")
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch hourly data for {symbol}: {e}")
        return pd.DataFrame()


def save_hourly_csv(df, filename=HOURLY_CSV_PATH):
    path = os.path.abspath(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if df.empty:
        print("[ERROR] DataFrame is empty, skipping save.")
        return
    df.to_csv(path)
    print(f"[INFO] Hourly data saved to {path}, rows: {len(df)}")


# ========== 主流程 ==========
if __name__ == "__main__":
    mode = os.environ.get("MODE", "hourly").strip().lower()
    print(f"[DEBUG] MODE={mode}")
    print(f"[DEBUG] CWD={os.getcwd()}")

    if mode == "hourly":
        all_data = []
        for name, symbol in TICKERS.items():
            df = fetch_hourly_data(symbol)
            if not df.empty:
                df["Symbol"] = symbol
                all_data.append(df)

        if all_data:
            merged_df = pd.concat(all_data)
            save_hourly_csv(merged_df)
        else:
            print("[ERROR] No hourly data collected at all.")
    else:
        print(f"[INFO] MODE={mode}, skipping hourly data fetch.")
