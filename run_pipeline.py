#!/usr/bin/env python3
# run_pipeline.py
import os
import json
import datetime
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def weekly_pipeline():
    print("=== 每週策略更新任務 ===")
    df = fetch_ohlcv(SYMBOL, years=3)
    
    print("=== 生成策略 JSON (LLM) ===")
    strategy_json = generate_strategy_llm(df)
    
    print("=== 回測策略 ===")
    metrics = run_backtest(df, strategy_data=strategy_json, cash=1_000_000)
    
    weekly_info = {
        "asof": str(df.index[-1]),
        "strategy": strategy_json,
        "metrics": metrics
    }
    
    weekly_file = os.path.join(REPORT_DIR, "weekly_insight.json")
    with open(weekly_file, "w", encoding="utf-8") as f:
        json.dump(weekly_info, f, ensure_ascii=False, indent=2)
    print(f"Weekly insight saved: {weekly_file}")
    
    return weekly_info

def daily_job():
    print("=== 每日交易任務 ===")
    weekly_file = os.path.join(REPORT_DIR, "weekly_insight.json")
    
    if not os.path.exists(weekly_file):
        print("Weekly insight not found. Skip daily job.")
        return
    
    with open(weekly_file, "r", encoding="utf-8") as f:
        weekly_info = json.load(f)
    
    if "strategy" not in weekly_info:
        print("Strategy key not found in weekly info. Skip daily job.")
        return
    
    strategy_data = weekly_info["strategy"]
    
    res = run_daily_sim(SYMBOL, strategy_data=strategy_data, cash=1_000_000)
    
    daily_file = os.path.join(REPORT_DIR, "daily_signal.json")
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"Daily simulation saved: {daily_file}")
    
    return res

if __name__ == "__main__":
    today = datetime.date.today()
    weekday = today.weekday()

    if weekday == 5:  # 星期六
        weekly_pipeline()
    elif weekday < 5:  # 週一到週五
        daily_job()
    else:
        print("週日休市，無任務執行")
