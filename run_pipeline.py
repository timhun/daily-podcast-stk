#!/usr/bin/env python3
# run_pipeline.py
import os
import datetime
import json
import pandas as pd
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import make_weekly_report, generate_strategy_json
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def weekly_pipeline():
    print("=== 1) 拉資料 + 指標 ===")
    df = fetch_ohlcv(SYMBOL, years=3)

    print("\n=== 2) 生成週報 & LLM 策略 ===")
    weekly_report = make_weekly_report(df)
    strategy_data = generate_strategy_json(weekly_report)

    # 儲存策略 JSON
    strategy_file = os.path.join(REPORT_DIR, "strategy_data.json")
    with open(strategy_file, "w", encoding="utf-8") as f:
        json.dump({
            "weekly_report": weekly_report,
            "strategy_data": {
                "name": strategy_data["name"],
                "summary": strategy_data["summary"],
                "params": strategy_data["params"]
            }
        }, f, indent=2, ensure_ascii=False)
    print(f"策略 JSON 已儲存: {strategy_file}")

    print("\n=== 3) 回測（含 OOS 留出 6 個月）===")
    metrics = run_backtest(df, strategy_data, cash=1_000_000)
    print("回測績效：", metrics)

    # 簡單判斷是否部署
    if metrics["sharpe_ratio"] > 1.0 and metrics["max_drawdown"] < 0.2:
        print("策略通過，進入每日模擬交易階段")
    else:
        print("策略未通過，將在下週重新生成")

    # 儲存回測結果
    with open(os.path.join(REPORT_DIR, "backtest_report.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    return metrics

def daily_job():
    print("=== 每日模擬交易 ===")
    # 讀取最新策略 JSON
    strategy_file = os.path.join(REPORT_DIR, "strategy_data.json")
    if not os.path.exists(strategy_file):
        raise FileNotFoundError(f"{strategy_file} 不存在，無法執行每日模擬")
    with open(strategy_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    strategy_data = generate_strategy_json(data["weekly_report"])  # 生成 callable signal

    res = run_daily_sim(SYMBOL, strategy_data, cash=1_000_000)
    print("當日模擬結果：", res)

    # 儲存每日模擬結果
    for k, v in res.items():
        with open(os.path.join(REPORT_DIR, f"daily_{k}.txt"), "w", encoding="utf-8") as f:
            f.write(str(v))
    return res

if __name__ == "__main__":
    today = datetime.date.today()
    weekday = today.weekday()

    if weekday == 5:  # 星期六跑 weekly pipeline
        print("=== 每週策略更新任務 ===")
        weekly_pipeline()
    elif weekday < 5:  # 週一到週五跑 daily job
        print("=== 每日交易任務 ===")
        daily_job()
    else:
        print("週日休市，無任務執行")
