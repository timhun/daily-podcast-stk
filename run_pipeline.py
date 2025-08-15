#!/usr/bin/env python3
# run_pipeline.py
import os
import json
import datetime as dt

# 依現有專案結構導入：JSON pipeline 版本
from src.data_fetch import fetch_ohlcv
from src.strategy_llm_groq import generate_strategy_llm
from src.backtest_json import run_backtest_json, run_daily_sim_json

SYMBOL = os.environ.get("SYMBOL", "0050.TW")
REPORT_DIR = os.environ.get("REPORT_DIR", "reports")
HISTORY_FILE = os.environ.get("HISTORY_FILE", "strategy_history.json")
USE_LLM = os.environ.get("USE_LLM", "1") == "1"

# 目標報酬率（給 LLM 參考用，不一定每個策略都會使用）
TARGET_RETURN = float(os.environ.get("TARGET_RETURN", "0.02"))  # 2%

os.makedirs(REPORT_DIR, exist_ok=True)


def _to_df_json(df):
    """把 DataFrame 轉成 JSON 可序列化的 dict（index -> row dict）"""
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
    # 取 3 年日K做週期性回測學習
    df = fetch_ohlcv(SYMBOL, years=3, interval="1d")
    df_json = _to_df_json(df)

    # 生成策略 JSON（帶記憶庫）
    try:
        strategy_data = generate_strategy_llm(
            df_json,
            history_file=HISTORY_FILE,
            target_return=TARGET_RETURN,  # 若你的函式不接受此參數，會在 except 改用不帶參數
        )
    except TypeError:
        strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    # 回測（JSON 版）
    metrics = run_backtest_json(df, strategy_data)

    # 保存 backtest 報告（供 Slack / Email / Artifact）
    weekly_report = {"asof": str(df.index[-1]), "strategy": strategy_data, "metrics": metrics}
    _save(os.path.join(REPORT_DIR, "backtest_report.json"), weekly_report)
    print("每週回測完成：", weekly_report)
    return weekly_report


def daily_pipeline():
    print("=== 每日模擬交易（日K）===")
    # 讀取最新策略（若沒跑過 weekly，走 HOLD 安全預設）
    weekly_report = _load_json(os.path.join(REPORT_DIR, "backtest_report.json"), {})
    strategy_data = weekly_report.get("strategy", {"signal": "hold", "size_pct": 0})

    # 取近半年資料，當日模擬
    df = fetch_ohlcv(SYMBOL, years=1, interval="1d").last("180D")
    daily_res = run_daily_sim_json(df, strategy_data)

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
    print("每日模擬完成：", out)
    return out


def hourly_pipeline():
    print("=== 每小時自我學習 + 短線模擬（小時K，90天）===")
    # 取 90 天小時K（yfinance: 60m）
    df = fetch_ohlcv(SYMBOL, years=1, interval="60m")
    # 只保留近 90 天
    try:
        df = df.last("90D")
    except Exception:
        # 若是舊版 pandas 沒 .last("90D")，fallback：
        cutoff = df.index.max() - dt.timedelta(days=90)
        df = df[df.index >= cutoff]

    df_json = _to_df_json(df)

    # 生成短線策略（帶記憶庫 + 目標報酬率 2%）
    try:
        strategy_data = generate_strategy_llm(
            df_json,
            history_file=HISTORY_FILE,
            target_return=TARGET_RETURN,
        )
    except TypeError:
        strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE)

    # 用小時K 做「短線模擬」（你的 backtest_json 可視情況擴充）
    daily_res = run_daily_sim_json(df, strategy_data)

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
    print("每小時短線模擬完成：", out)
    return out


def main():
    """
    執行策略：
      - 週六（weekday == 5）：weekly
      - 週一~週五：先跑 hourly；若在 09:00 台北時間的那次排程，當天也會跑 daily
      - 其他時間：只跑 hourly
    也可用 MODE 覆蓋：MODE=hourly|daily|weekly|auto（預設）
    """
    mode = os.environ.get("MODE", "auto")
    now_utc = dt.datetime.utcnow()
    # 台北時間（UTC+8）
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

    # auto 模式
    if weekday == 5:  # 週六
        weekly_pipeline()
    elif 0 <= weekday <= 4:  # 週一到週五
        # 每小時先跑短線學習/模擬
        hourly_pipeline()
        # 在每天 09:00 台北時間由排程觸發，再補跑一次日K的 daily 模擬
        if hour_local == 9:
            daily_pipeline()
    else:
        # 週日：只跑 hourly（若你完全不想跑，可直接 return）
        hourly_pipeline()


if __name__ == "__main__":
    main()
