#!/usr/bin/env python3
# full_pipeline_csv_hourly_rolling.py
import os
import json
import datetime as dt
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from dateutil import tz

# ====== 設定 ======
SYMBOL = os.environ.get("SYMBOL", "0050.TW")
REPORT_DIR = os.environ.get("REPORT_DIR", "reports")
HISTORY_FILE = os.environ.get("HISTORY_FILE", "strategy_history.json")
USE_LLM = os.environ.get("USE_LLM", "1") == "1"
TARGET_RETURN = float(os.environ.get("TARGET_RETURN", "0.02"))
TAI_TZ = tz.gettz("Asia/Taipei")
Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)

# ====== Data Fetch ======
def _ensure_cols_flat(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        cols = ["_".join([str(x) for x in col]).strip().lower() for col in df.columns.values]
        df.columns = cols
    else:
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    want = {"open": None, "high": None, "low": None, "close": None, "volume": None}
    for c in df.columns:
        for w in want.keys():
            if c.endswith("_" + w) or c == w or c.endswith("." + w) or ("_"+w+"_") in c or c.split("_")[-1] == w:
                if want[w] is None:
                    want[w] = c
    for w in want:
        if want[w] is None:
            for c in df.columns:
                if w in c and want[w] is None:
                    want[w] = c
    missing = [k for k, v in want.items() if v is None]
    if missing:
        raise RuntimeError(f"找不到必要欄位: {missing}. 現有欄位: {list(df.columns)}")
    return df.rename(columns={want["open"]:"open", want["high"]:"high",
                              want["low"]:"low", want["close"]:"close", want["volume"]:"volume"})

def fetch_ohlcv(symbol: str, start=None, end=None, interval="1d") -> pd.DataFrame:
    df = yf.download(symbol, start=start, end=end, interval=interval,
                     auto_adjust=True, progress=False, threads=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance 下載失敗或無資料")
    df = _ensure_cols_flat(df)
    if df.index.tz is None:
        df.index = df.index.tz_localize(dt.timezone.utc)
    df.index = df.index.tz_convert(TAI_TZ)
    return df[["open", "high", "low", "close", "volume"]].dropna()

def save_csv(df: pd.DataFrame, filename: str) -> str:
    path = os.path.join(REPORT_DIR, filename)
    df.to_csv(path)
    print(f"[INFO] Saved {filename}")
    return path

def load_or_update_csv(symbol: str, filename: str, interval="1d", last_days=None) -> pd.DataFrame:
    """增量更新 CSV，如果 hourly.csv 則自動保留 last_days"""
    path = os.path.join(REPORT_DIR, filename)
    now = dt.datetime.now(dt.timezone.utc)
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = df.index.tz_localize(TAI_TZ, ambiguous='NaT', nonexistent='shift_forward')
        last_date = df.index.max()
        # 抓 last_date 後的新資料
        df_new = fetch_ohlcv(symbol, start=(last_date + dt.timedelta(minutes=1)).date(),
                             end=now.date()+dt.timedelta(days=1), interval=interval)
        if not df_new.empty:
            df = pd.concat([df, df_new])
            df = df[~df.index.duplicated(keep='last')]
            # 如果是 hourly.csv，只保留最近 last_days
            if last_days and interval.endswith("m"):
                cutoff = df.index.max() - dt.timedelta(days=last_days)
                df = df[df.index >= cutoff]
            save_csv(df, filename)
        print(f"[INFO] Loaded and updated {filename} CSV")
    else:
        # 初次抓資料
        start = now - dt.timedelta(days=365 if interval=="1d" else 30)
        df = fetch_ohlcv(symbol, start=start.date(), end=now.date()+dt.timedelta(days=1), interval=interval)
        if last_days and interval.endswith("m"):
            cutoff = df.index.max() - dt.timedelta(days=last_days)
            df = df[df.index >= cutoff]
        save_csv(df, filename)
        print(f"[INFO] Created {filename} CSV")
    return df

# ====== 技術指標 ======
def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = -delta.clip(upper=0).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - (100/(1+rs))

def atr(df, n=14):
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift()).abs()
    tr3 = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    px = out["close"]
    out["ret"] = px.pct_change()
    out["ma5"]  = px.rolling(5).mean()
    out["ma20"] = px.rolling(20).mean()
    out["ma60"] = px.rolling(60).mean()
    out["rsi14"] = rsi(px, 14)
    out["bb_mid"] = px.rolling(20).mean()
    out["bb_std"] = px.rolling(20).std()
    out["bb_up"]  = out["bb_mid"] + 2*out["bb_std"]
    out["bb_dn"]  = out["bb_mid"] - 2*out["bb_std"]
    out["atr14"]  = atr(out, 14)
    return out.dropna()

# ====== 假策略 / 回測 ======
def generate_strategy_llm(df_json, history_file=None, target_return=0.02):
    last_close = list(df_json.values())[-1]["close"]
    return {"signal": "buy" if last_close % 2 == 0 else "hold", "size_pct": 0.1}

def run_backtest_json(df, strategy_data):
    return {"sharpe": 1.0, "max_drawdown": 0.1}

def run_daily_sim_json(df, strategy_data):
    last_close = df["close"].iloc[-1]
    return {"signal": strategy_data.get("signal", "hold"),
            "size_pct": strategy_data.get("size_pct", 0),
            "price": last_close,
            "note": ""}

# ====== Pipeline ======
def weekly_pipeline():
    print("=== 每週策略生成 / 回測（日K）===")
    df = load_or_update_csv(SYMBOL, "daily.csv", interval="1d", last_days=180)
    df_json = df.fillna(0).to_dict(orient="index")
    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE, target_return=TARGET_RETURN)
    metrics = run_backtest_json(df, strategy_data)
    report = {"asof": str(df.index[-1]), "strategy": strategy_data, "metrics": metrics}
    save_csv(pd.DataFrame([report]), "weekly_report.json")
    print("[INFO] Weekly pipeline done:", report)
    return report

def daily_pipeline():
    print("=== 每日模擬交易（日K）===")
    df = load_or_update_csv(SYMBOL, "daily.csv", interval="1d", last_days=180)
    df_json = df.fillna(0).to_dict(orient="index")
    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE, target_return=TARGET_RETURN)
    daily_res = run_daily_sim_json(df, strategy_data)
    out = {"asof": str(df.index[-1]), "symbol": SYMBOL,
           "signal": daily_res.get("signal"), "size_pct": daily_res.get("size_pct"),
           "price": daily_res.get("price"), "note": daily_res.get("note"),
           "strategy_used": strategy_data}
    save_csv(pd.DataFrame([out]), "daily_sim.json")
    print("[INFO] Daily pipeline done:", out)
    return out

def hourly_pipeline():
    print("=== 每小時短線模擬（小時K，7天）===")
    df = load_or_update_csv(SYMBOL, "hourly.csv", interval="60m", last_days=7)
    df_json = df.fillna(0).to_dict(orient="index")
    strategy_data = generate_strategy_llm(df_json, history_file=HISTORY_FILE, target_return=TARGET_RETURN)
    hourly_res = run_daily_sim_json(df, strategy_data)
    out = {"asof": str(df.index[-1]), "symbol": SYMBOL,
           "signal": hourly_res.get("signal"), "size_pct": hourly_res.get("size_pct"),
           "price": hourly_res.get("price"), "note": hourly_res.get("note"),
           "strategy_used": strategy_data, "mode": "hourly"}
    save_csv(pd.DataFrame([out]), "hourly_sim.json")
    print("[INFO] Hourly pipeline done:", out)
    return out

def main():
    mode = os.environ.get("MODE", "auto")
    now_utc = dt.datetime.utcnow()
    taipei_now = now_utc + dt.timedelta(hours=8)
    weekday = taipei_now.weekday()
    hour_local = taipei_now.hour
    print(f"[DEBUG] now_utc={now_utc} taipei_now={taipei_now} mode={mode}")

    if mode == "weekly":
        weekly_pipeline()
    elif mode == "daily":
        daily_pipeline()
    elif mode == "hourly":
        hourly_pipeline()
    else:
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