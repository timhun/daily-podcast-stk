# run_pipeline.py
import os
import datetime
import json
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim

SYMBOL = "0050.TW"
REPORT_DIR = "reports"
HISTORY_FILE = "strategy_history.json"
os.makedirs(REPORT_DIR, exist_ok=True)

def weekly_pipeline():
    print("=== 每週策略生成任務 ===")
    df = fetch_ohlcv(SYMBOL, years=3)
    df_json = df.fillna(0).to_dict(orient="index")

    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    metrics = run_backtest(df, strategy_data)
    print("回測績效：", metrics)

    # 保存報告
    report_path = os.path.join(REPORT_DIR, "backtest_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"strategy": strategy_data, "metrics": metrics}, f, ensure_ascii=False, indent=2)

    return {"strategy": strategy_data, "metrics": metrics}

def daily_job():
    print("=== 每日模擬交易任務 ===")
    # 讀取最新策略
    weekly_report_path = os.path.join(REPORT_DIR, "backtest_report.json")
    if os.path.exists(weekly_report_path):
        with open(weekly_report_path, "r", encoding="utf-8") as f:
            weekly_info = json.load(f)
        strategy_data = weekly_info.get("strategy", {"signal": "hold", "size_pct": 0})
    else:
        strategy_data = {"signal": "hold", "size_pct": 0}

    df_today = fetch_ohlcv(SYMBOL, years=0.5)  # 半年內資料
    daily_res = run_daily_sim(SYMBOL, strategy_data)
    
    # 保存每日模擬結果
    daily_report_path = os.path.join(REPORT_DIR, "daily_sim.json")
    with open(daily_report_path, "w", encoding="utf-8") as f:
        json.dump(daily_res, f, ensure_ascii=False, indent=2)

    print("當日模擬結果：", daily_res)
    return daily_res

if __name__ == "__main__":
    today = datetime.date.today()
    weekday = today.weekday()

    if weekday == 5:  # 星期六跑 weekly pipeline
        weekly_pipeline()
    elif weekday < 5:  # 週一到週五跑 daily job
        daily_job()
    else:
        print("週日休市，無任務執行")
