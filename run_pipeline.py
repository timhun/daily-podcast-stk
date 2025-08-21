#!/usr/bin/env python3
# run_pipeline.py
import os
import json
import importlib.util
from datetime import datetime

# === src 引用 ===
from src.data_fetch import fetch_ohlcv
from src.daily_sim import run_daily_sim
from src.backtest import run_backtest
from src.notify import send_to_notion, send_to_slack

STRAT_CAND = "strategy_candidate.py"
STRAT_OUT = "strategy_out.py"


# === 每日任務 ===
def daily_pipeline():
    print("=== 每日模擬 ===")
    df = fetch_ohlcv("QQQ", years=1)
    res = run_daily_sim("QQQ", STRAT_CAND, cash=1_000_000)

    signal = {
        "symbol": "QQQ",
        "date": str(df.index[-1].date()),
        "metrics": res,
    }

    with open("signal.json", "w") as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)
    print("✅ 信號已存成 signal.json")

    if os.getenv("NOTION_TOKEN") and os.getenv("NOTION_DB"):
        send_to_notion(signal)
    if os.getenv("SLACK_WEBHOOK"):
        send_to_slack(f"📊 每日交易信號: {json.dumps(signal, ensure_ascii=False)}")

    return signal


# === 每週任務 ===
def weekly_pipeline():
    print("=== 每週回測 ===")
    df = fetch_ohlcv("QQQ", years=5)
    metrics = run_backtest(
        df, strategy_path=STRAT_CAND, cash=1_000_000, out_path=STRAT_OUT
    )

    result = {
        "symbol": "QQQ",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
    }

    with open("backtest.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("✅ 回測結果已存成 backtest.json")
    print("✅ 策略已更新為 strategy_out.py")

    if os.getenv("NOTION_TOKEN") and os.getenv("NOTION_DB"):
        send_to_notion(result)
    if os.getenv("SLACK_WEBHOOK"):
        send_to_slack(f"📈 每週回測結果: {json.dumps(result, ensure_ascii=False)}")

    return result


# === 主程式入口 ===
if __name__ == "__main__":
    mode = os.getenv("JOB_MODE", "daily")

    if mode == "daily":
        daily_pipeline()
    elif mode == "weekly":
        weekly_pipeline()
    else:
        print(f"⚠️ 未知模式: {mode}，請設置 JOB_MODE=daily 或 weekly")
