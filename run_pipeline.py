#!/usr/bin/env python3
# run_pipeline.py
import os
import datetime
import json
from src.data_fetch import fetch_ohlcv
from src.backtest import run_backtest
from src.daily_sim import run_daily_sim
from src.strategy_llm_groq import generate_strategy_with_groq

SYMBOL = "0050.TW"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

STRAT_JSON = os.path.join(REPORT_DIR, "strategy_generated.json")


def weekly_pipeline():
    print("=== 1) 拉資料 + 指標 ===")
    df = fetch_ohlcv(SYMBOL, years=3)

    print("\n=== 2) LLM 自動生成策略 ===")
    strategy_data = generate_strategy_with_groq()
    with open(STRAT_JSON, "w", encoding="utf-8") as f:
        json.dump(strategy_data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 策略 JSON 已儲存：{STRAT_JSON}")

    print("\n=== 3) 回測（OOS 6 個月） ===")
    metrics = run_backtest(df, strategy_path=None, strategy_data=strategy_data, cash=1_000_000)
    metrics_file = os.path.join(REPORT_DIR, "backtest_report.json")
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print("[INFO] 回測結果已儲存:", metrics_file)

    if metrics["sharpe_ratio"] > 1.0 and metrics["max_drawdown"] < 0.2:
        print("[INFO] 策略通過，可進入每日模擬階段")
    else:
        print("[INFO] 策略未通過，將在下週重新生成")

    return metrics


def daily_job():
    print("=== 每日模擬交易 ===")
    if not os.path.exists(STRAT_JSON):
        print("[WARN] 策略 JSON 不存在，先生成一次")
        generate_strategy_with_groq()

    with open(STRAT_JSON, "r", encoding="utf-8") as f:
        strategy_data = json.load(f)

    res = run_daily_sim(SYMBOL, strategy_path=None, strategy_data=strategy_data, cash=1_000_000)
    # 儲存每日交易結果
    for key in ["signal", "price", "size"]:
        with open(os.path.join(REPORT_DIR, f"daily_{key}.txt"), "w", encoding="utf-8") as f:
            f.write(str(res.get(key, "N/A")))
    print("[INFO] 當日模擬結果已儲存至 reports/")

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
        print("[INFO] 週日休市，無任務執行")
