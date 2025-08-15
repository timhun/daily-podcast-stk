#!/usr/bin/env python3
# run_pipeline.py
import os
import json
import datetime as dt
from pathlib import Path

from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest_json import run_backtest_json, run_daily_sim_json

SYMBOL = os.environ.get("SYMBOL", "0050.TW")
REPORT_DIR = os.environ.get("REPORT_DIR", "reports")
HISTORY_FILE = os.environ.get("HISTORY_FILE", "strategy_history.json")
USE_LLM = os.environ.get("USE_LLM", "1") == "1"
TARGET_RETURN = float(os.environ.get("TARGET_RETURN", "0.02"))

Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)

def _to_df_json(df):
    return df.fillna(0).to_dict(orient="index")

def _save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def weekly_pipeline():
    print("=== 每週策略生成 / 回測（使用日K）===")
    df = fetch_ohlcv(SYMBOL, years=3, interval="1d")
    print("[DEBUG] Daily OHLCV df empty?", df.empty)
    print("[DEBUG] df head:\n", df.head())
    df_json = _to_df_json(df)

    try:
        strategy_data = generate_strategy_llm(
            df_json,
            history_file=HISTORY_FILE,
            target_return=TARGET_RETURN,
        )
    except TypeError:
        strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    print("[DEBUG] Generated weekly strategy:", strategy_data)

    metrics = run_backtest_json(df, strategy_data)
    print("[DEBUG] Weekly backtest metrics:", metrics)

    weekly_report = {"asof": str(df.index[-1]), "strategy": strategy_data, "metrics": metrics}
    _save(os.path.join(REPORT_DIR, "backtest_report.json"), weekly_report)
    return weekly_report

def daily_pipeline():
    print("=== 每日模擬交易（日K）===")
    weekly_report = _load_json(os.path.join(REPORT_DIR, "backtest_report.json"), {})
    strategy_data = weekly_report.get("strategy", {"signal": "hold", "size_pct": 0})

    df = fetch_ohlcv(SYMBOL, years=1, interval="1d").last("180D")
    print("[DEBUG] Daily sim df empty?", df.empty)
    print("[DEBUG] df head:\n", df.head())

    daily_res = run_daily_sim_json(df, strategy_data)
    print("[DEBUG] Daily sim result:", daily_res)

    out = {
        "asof": str(df.index[-1]) if len(df.index) else dt.date.today().isoformat(),
        "symbol": SYMBOL,
        "signal": daily_res.get("signal", "hold"),
        "size_pct": daily_res.get("size_pct", 0),
        "price": daily_res.get("price"),
        "note": daily_res.get("note", ""),
        "strategy_used": strategy_data,
    }
    _save(os.path.join(REPORT_DIR, "daily_sim.json"), out)
    return out

def hourly_pipeline():
    print("=== 每小時自我學習 + 短線模擬（小時K，90天）===")
    df = fetch_ohlcv(SYMBOL, years=1, interval="60m")
    try:
        df = df.last("90D")
    except Exception:
        cutoff = df.index.max() - dt.timedelta(days=90)
        df = df[df.index >= cutoff]

    print("[DEBUG] Hourly df empty?", df.empty)
    print("[DEBUG] df head:\n", df.head())

    df_json = _to_df_json(df)
    try:
        strategy_data = generate_strategy_llm(
            df_json,
            history_file=HISTORY_FILE,
            target_return=TARGET_RETURN,
        )
    except TypeError:
        strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    print("[DEBUG] Generated hourly strategy:", strategy_data)

    daily_res = run_daily_sim_json(df, strategy_data)
    print("[DEBUG] Hourly sim result:", daily_res)

    out = {
        "asof": str(df.index[-1]) if len(df.index) else dt.datetime.utcnow().isoformat(),
        "symbol": SYMBOL,
        "signal": daily_res.get("signal", "hold"),
        "size_pct": daily_res.get("size_pct", 0),
        "price": daily_res.get("price"),
        "note": daily_res.get("note", ""),
        "strategy_used": strategy_data,
        "mode": "hourly",
    }
    _save(os.path.join(REPORT_DIR, "hourly_sim.json"), out)
    return out

def main():
    mode = os.environ.get("MODE", "auto")
    now_utc = dt.datetime.utcnow()
    taipei_now = now_utc + dt.timedelta(hours=8)
    weekday = taipei_now.weekday()
    hour_local = taipei_now.hour

    print(f"[DEBUG] now_utc={now_utc.isoformat()} taipei_now={taipei_now.isoformat()} mode={mode}")

    if mode == "weekly":
        weekly_pipeline()
        return
    if mode == "daily":
        daily_pipeline()
        return
    if mode == "hourly":
        hourly_pipeline()
        return

    if weekday == 5:
        weekly_pipeline()
    elif 0 <= weekday <= 4:
        hourly_pipeline()
        if hour_local == 9:
            daily_pipeline()
    else:
        hourly_pipeline()

if __name__ == "__main__":
    main()