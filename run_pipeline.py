#!/usr/bin/env python3
# run_pipeline.py
import os, json, datetime
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy
from src.backtest_json import run_backtest_json, run_daily_sim_json

REPORT_DIR = "reports"
HISTORY_FILE = "strategy_history.json"
SYMBOL = "0050.TW"
CASH = 1_000_000

os.makedirs(REPORT_DIR, exist_ok=True)

# --- 讀取歷史策略記錄 ---
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        strategy_history = json.load(f)
else:
    strategy_history = {}

# --- 取得今天日期 ---
today = datetime.date.today()
weekday = today.weekday()

def weekly_pipeline():
    df = fetch_ohlcv(SYMBOL, years=3)
    strategy_data = generate_strategy(df, history=strategy_history)
    backtest_metrics = run_backtest_json(df, strategy_data, cash=CASH)

    # 更新歷史策略記錄
    strategy_history[str(today.isoformat())] = {
        "sharpe": backtest_metrics["sharpe_ratio"],
        "max_drawdown": backtest_metrics["max_drawdown"]
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(strategy_history, f, indent=2, ensure_ascii=False)

    # 存回報表
    with open(os.path.join(REPORT_DIR, "weekly_insight.json"), "w", encoding="utf-8") as f:
        json.dump({"strategy": strategy_data, "metrics": backtest_metrics}, f, indent=2)
    return strategy_data, backtest_metrics

def daily_job():
    df = fetch_ohlcv(SYMBOL, years=1)
    if os.path.exists(os.path.join(REPORT_DIR, "weekly_insight.json")):
        with open(os.path.join(REPORT_DIR, "weekly_insight.json"), "r", encoding="utf-8") as f:
            weekly_info = json.load(f)
        strategy_data = weekly_info["strategy"]
    else:
        strategy_data, _ = weekly_pipeline()

    daily_res = run_daily_sim_json(df, strategy_data, cash=CASH)

    # 存每日報表
    with open(os.path.join(REPORT_DIR, "daily_signal.txt"), "w", encoding="utf-8") as f:
        f.write(daily_res.get("signal", "hold"))
    with open(os.path.join(REPORT_DIR, "daily_price.txt"), "w", encoding="utf-8") as f:
        f.write(str(daily_res.get("price", "N/A")))
    with open(os.path.join(REPORT_DIR, "daily_size.txt"), "w", encoding="utf-8") as f:
        f.write(str(daily_res.get("size_pct", "N/A")))
    with open(os.path.join(REPORT_DIR, "last_daily_signal.json"), "w", encoding="utf-8") as f:
        json.dump(daily_res, f, indent=2)
    return daily_res

if __name__ == "__main__":
    if weekday == 5:  # Saturday
        print("=== 每週策略更新任務 ===")
        weekly_pipeline()
    elif weekday < 5:  # Mon-Fri
        print("=== 每日交易任務 ===")
        daily_job()
    else:
        print("週日休市，無任務執行")
