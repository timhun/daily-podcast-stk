#!/usr/bin/env python3
# src/hourly_sim.py
import os
import json
import datetime
import yfinance as yf
from src.strategy_llm_groq import generate_strategy_llm

SYMBOL = "0050.TW"
HISTORY_FILE = "strategy_history.json"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def fetch_hourly_ohlcv(symbol=SYMBOL, days=90):
    """
    取得過去 days 天，每小時的 OHLCV 資料
    """
    df = yf.download(symbol, period=f"{days}d", interval="60m")
    if df.empty:
        raise ValueError("No data fetched from Yahoo Finance")
    df.fillna(0, inplace=True)
    return df.to_dict(orient="index")

def run_hourly_sim():
    print("=== 每日小時 K 線短線策略生成 ===")
    df_json = fetch_hourly_ohlcv()
    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    # 儲存報告
    hourly_report_path = os.path.join(REPORT_DIR, "hourly_sim.json")
    with open(hourly_report_path, "w", encoding="utf-8") as f:
        json.dump(strategy_data, f, ensure_ascii=False, indent=2)

    print("小時策略結果：", strategy_data)
    return strategy_data

if __name__ == "__main__":
    run_hourly_sim()
