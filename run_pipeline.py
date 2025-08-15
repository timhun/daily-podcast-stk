#!/usr/bin/env python3
# run_pipeline.py
import os
import datetime
import json
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest_json import run_backtest_json, run_daily_sim_json
from src.hourly_sim import run_hourly_sim

SYMBOL = "0050.TW"
REPORT_DIR = "reports"
HISTORY_FILE = "strategy_history.json"
os.makedirs(REPORT_DIR, exist_ok=True)

def weekly_pipeline():
    print("=== 每週策略生成任務 ===")
    df = fetch_ohlcv(SYMBOL, years=3)
    df_json = df.fillna(0).to_dict(orient="index")
    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)
    metrics = run_backtest_json(df_json, strategy_data)

    report_path = os.path.join(REPORT_DIR, "backtest_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"strategy": strategy_data, "metrics": metrics}, f, ensure_ascii=False, indent=2)
    return {"strategy": strategy_data, "metrics": metrics}

def daily_job():
    print("=== 每日模擬交易任務 ===")
    weekly_report_path = os.path.join(REPORT_DIR, "backtest_report.json")
    if os.path.exists(weekly_report_path):
        with open(weekly_report_path, "r", encoding="utf-8") as f:
            weekly_info = json.load(f)
        strategy_data = weekly_info.get("strategy", {"signal": "hold", "size_pct": 0})
    else:
        strategy_data = {"signal": "hold", "size_pct": 0}

    df_today = fetch_ohlcv(SYMBOL, years=0.5)
    daily_res = run_daily_sim_json(df_today, strategy_data)

    daily_report_path = os.path.join(REPORT_DIR, "daily_sim.json")
    with open(daily_report_path, "w", encoding="utf-8") as f:
        json.dump(daily_res, f, ensure_ascii=False, indent=2)

    print("日 K 模擬結果：", daily_res)

    # 小時短線策略（非盤中 18:00 以後）
    now = datetime.datetime.now()
    if now.hour >= 18:
        hourly_res = run_hourly_sim()
        print("小時策略完成")
    else:
        hourly_res = None

    return {"daily": daily_res, "hourly": hourly_res}

if __name__ == "__main__":
    today = datetime.date.today()
    weekday = today.weekday()

    if weekday == 5:
        weekly_pipeline()
    elif weekday < 5:
        daily_job()
    else:
        print("週日休市，無任務執行")
