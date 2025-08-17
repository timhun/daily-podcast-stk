# scripts/data_collector.py
import os
import re
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import numpy as np
import yfinance as yf

# ---------- Paths ----------
DATA_DIR = "data"
LOG_DIR = "logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Logger ----------
logger = logging.getLogger("data_collector")
logger.setLevel(logging.INFO)

fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "data_collector.log"),
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8"
)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)


# ---------- Helpers ----------
def _safe_filename(symbol: str) -> str:
    """避免檔名出現 ^ 或奇怪字元"""
    name = symbol.replace("^", "INDEX_")
    return re.sub(r"[^A-Za-z0-9._\-]", "_", name)


def _retry_download(symbol: str, start: datetime, end: datetime,
                    interval: str, auto_adjust=False, tries=3, sleep=2):
    """重試下載，避免 yfinance 偶爾失敗"""
    last_err = None
    for i in range(tries):
        try:
            df = yf.download(
                symbol,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False,
                threads=True,
            )
            if df is not None and not df.empty:
                return df
            last_err = RuntimeError("Empty dataframe")
        except Exception as e:
            last_err = e
        time.sleep(sleep)
    raise last_err or RuntimeError("yfinance unknown error")


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """強制轉數字，避免 object dtype"""
    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _pct_checks(df: pd.DataFrame, symbol: str) -> List[str]:
    """檢查異常漲跌幅 / 跳空"""
    msgs = []
    if df.empty:
        return msgs
    if "Close" not in df.columns:
        msgs.append(f"{symbol}: 缺少 Close 欄位")
        return msgs

    close = df["Close"].astype(float)
    pct = close.pct_change() * 100

    if (pct.abs() > 20).any():
        count = int((pct.abs() > 20).sum())
        msgs.append(f"{symbol}: 發現 {count} 筆漲跌幅超過 ±20% (資料或除權息異常?)")

    jump = close.pct_change().abs() > 0.15
    if jump.any():
        msgs.append(f"{symbol}: 發現相鄰價格跳躍 {int(jump.sum())} 筆（>15%）")

    return msgs


def _direction_consistency(main_df: pd.DataFrame, bench_df: pd.DataFrame, label: str) -> str:
    """
    粗略一致性檢查：近 N 期，方向一致比例 (sign)，低於 40% 警告
    """
    try:
        N = min(20, len(main_df), len(bench_df))
        if N < 5:
            return ""
        m = main_df["Close"].astype(float).tail(N).pct_change().dropna()
        b = bench_df["Close"].astype(float).tail(N).pct_change().dropna()
        idx = m.index.intersection(b.index)
        if len(idx) < 5:
            return ""
        agree = (np.sign(m.loc[idx]) == np.sign(b.loc[idx])).mean()
        if agree < 0.4:
            return f"{label}: 近{len(idx)}期與基準方向一致率 {agree:.2f}，偏低（可能脫鉤或資料異常）。"
        return ""
    except Exception as e:
        return f"{label}: 一致性檢查失敗 {e}"


# ---------- Core ----------
def _download_one(symbol: str, start: datetime, end: datetime,
                  interval: str, keep_rows: int) -> pd.DataFrame:
    df = _retry_download(symbol, start, end, interval=interval, auto_adjust=False)
    if df.empty:
        return df

    df["Symbol"] = symbol
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    df = df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Symbol"]].copy()
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date"}, inplace=True)
    df = _coerce_numeric(df)

    if interval == "1d":
        df = df.tail(keep_rows)
    else:
        cutoff = end - timedelta(days=14)
        df = df[pd.to_datetime(df["Date"]) >= cutoff]

    return df


def collect_from_config(config_path: str = "config.json") -> Dict[str, str]:
    """
    config.json 範例：
    {
      "symbols": ["0050.TW", "QQQ", "^GSPC"],
      "benchmarks": {"0050.TW": "^TWII", "QQQ": "^NDX"},
      "hourly_symbols": ["0050.TW", "QQQ"]
    }
    """
    if not os.path.exists(config_path):
        cfg = {
            "symbols": ["0050.TW", "QQQ", "^GSPC"],
            "benchmarks": {"0050.TW": "^TWII", "QQQ": "^NDX", "^GSPC": "^GSPC"},
            "hourly_symbols": ["0050.TW", "QQQ"]
        }
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    now = datetime.utcnow()
    start_daily = now - timedelta(days=365)
    start_hourly = now - timedelta(days=14)

    summary = {}

    # === 日線 ===
    for sym in cfg.get("symbols", []):
        try:
            df_d = _download_one(sym, start_daily, now, "1d", keep_rows=300)
            fn = os.path.join(DATA_DIR, f"daily_{_safe_filename(sym)}.csv")
            df_d.to_csv(fn, index=False, encoding="utf-8")
            logger.info(f"[Daily] {sym} -> {fn}, rows={len(df_d)}")

            for w in _pct_checks(df_d, sym):
                logger.warning(w)

            bench = cfg.get("benchmarks", {}).get(sym)
            if bench:
                try:
                    df_b = _download_one(bench, start_daily, now, "1d", keep_rows=300)
                    msg = _direction_consistency(df_d, df_b, f"{sym} vs {bench}")
                    if msg:
                        logger.warning(msg)
                except Exception as e:
                    logger.warning(f"{sym} 基準 {bench} 下載失敗: {e}")
        except Exception as e:
            logger.error(f"{sym} 日線下載失敗: {e}")

    # === 小時線 ===
    for sym in cfg.get("hourly_symbols", []):
        try:
            df_h = _download_one(sym, start_hourly, now, "1h", keep_rows=100000)
            fn = os.path.join(DATA_DIR, f"hourly_{_safe_filename(sym)}.csv")
            df_h.to_csv(fn, index=False, encoding="utf-8")
            logger.info(f"[Hourly] {sym} -> {fn}, rows={len(df_h)}")

            for w in _pct_checks(df_h, sym):
                logger.warning(w)
        except Exception as e:
            logger.error(f"{sym} 小時線下載失敗: {e}")

    summary["generated_at"] = datetime.utcnow().isoformat() + "Z"
    return summary


if __name__ == "__main__":
    collect_from_config()