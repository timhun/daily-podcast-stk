#!/usr/bin/env python3
# run_pipeline.py

import os
import datetime as dt
from dateutil import tz
from pathlib import Path
import pandas as pd
import yfinance as yf

# ====== 基本設定 ======
TAI_TZ = tz.gettz("Asia/Taipei")
MODE = os.environ.get("MODE", "daily")
SYMBOL = os.environ.get("SYMBOL", "0050.TW")

# ====== 工具函式 ======
def _ensure_cols_flat(df: pd.DataFrame) -> pd.DataFrame:
    """把 yfinance 可能回傳的 MultiIndex 攤平成單層欄位"""
    if isinstance(df.columns, pd.MultiIndex):
        cols = ["_".join([str(x) for x in col]).strip().lower() for x in df.columns.values]
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

    df2 = df.rename(columns={want["open"]:"open", want["high"]:"high",
                             want["low"]:"low", want["close"]:"close", want["volume"]:"volume"})
    return df2

def fetch_ohlcv(symbol: str, years: int = 3, interval="1d", fallback=False) -> pd.DataFrame:
    """下載 OHLCV"""
    print(f"[DEBUG] Fetching {interval} data for {symbol}...")
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=365*years + 60)

    df = yf.download(symbol, start=start.date(), end=end.date()+dt.timedelta(days=1),
                     interval=interval, auto_adjust=True, progress=False, threads=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance 下載失敗或無資料")
    print(f"[DEBUG] Raw data rows: {len(df)}")

    df = _ensure_cols_flat(df)
    if df.index.tz is None:
        df.index = df.index.tz_localize(dt.timezone.utc)
    df.index = df.index.tz_convert(TAI_TZ)

    if fallback and interval.endswith("m"):
        today = pd.Timestamp.now(TAI_TZ).normalize()
        if today not in df.index.normalize():
            print("[DEBUG] No data for today, filling with last row...")
            last_row = df.iloc[-1:]
            last_row.index = [pd.Timestamp.now(TAI_TZ)]
            df = pd.concat([df, last_row])

    return df[["open", "high", "low", "close", "volume"]].dropna()

def fetch_hourly_csv(symbol: str, output_file: str = "hourly.csv") -> pd.DataFrame:
    """抓取最近一週小時線資料並存 CSV"""
    df = fetch_ohlcv(symbol, years=0, interval="60m", fallback=True)
    cutoff = df.index.max() - dt.timedelta(days=7)
    df = df[df.index >= cutoff]

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file)
    print(f"[INFO] Hourly data saved to {output_file} ({len(df)} rows)")
    return df

# ====== 主流程 ======
if __name__ == "__main__":
    print(f"[INFO] Running pipeline in MODE={MODE}, SYMBOL={SYMBOL}")

    if MODE == "hourly":
        try:
            fetch_hourly_csv(SYMBOL, "hourly.csv")
        except Exception as e:
            print(f"[ERROR] Hourly fetch failed: {e}")

    elif MODE == "daily":
        print("[TODO] Daily mode 邏輯可在這裡實作")