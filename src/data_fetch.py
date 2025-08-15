# src/data_fetch.py
import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
from dateutil import tz

TAI_TZ = tz.gettz("Asia/Taipei")

def _ensure_cols_flat(df: pd.DataFrame) -> pd.DataFrame:
    """
    把 yfinance 可能回傳的 MultiIndex 欄位攤平成單層字串
    """
    if isinstance(df.columns, pd.MultiIndex):
        cols = ["_".join([str(x) for x in col]).strip().lower() for col in df.columns.values]
        df.columns = cols
    else:
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    colmap = {}
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

def fetch_ohlcv(symbol: str, interval="1d", years: int = 1, fallback: bool = False) -> pd.DataFrame:
    """
    下載 OHLCV
    interval: '1d' 或 '1h'
    fallback: 若今天資料缺，使用前一天收盤填充（只對 hourly 有效）
    """
    now_utc = dt.datetime.now(dt.timezone.utc)

    if interval.endswith("h"):
        # 小時線只抓最近 7 天
        start = now_utc - dt.timedelta(days=7)
    else:
        # 日線抓最近 N 年
        start = now_utc - dt.timedelta(days=365*years + 60)

    df = yf.download(symbol, start=start.date(), end=now_utc.date() + dt.timedelta(days=1),
                     interval=interval, auto_adjust=True, progress=False, threads=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance 下載失敗或無資料")

    df = _ensure_cols_flat(df)

    if df.index.tz is None:
        df.index = df.index.tz_localize(dt.timezone.utc)
    df.index = df.index.tz_convert(TAI_TZ)

    df = df[["open", "high", "low", "close", "volume"]].dropna()

    # fallback: 用前一天收盤填補今天小時缺失
    if fallback and interval.endswith("h"):
        today = dt.datetime.now(TAI_TZ).date()
        if today not in df.index.date:
            prev_day_close = df["close"].iloc[-1]
            hours = pd.date_range(start=dt.datetime.combine(today, dt.time(9,0), tzinfo=TAI_TZ),
                                  end=dt.datetime.combine(today, dt.time(15,0), tzinfo=TAI_TZ),
                                  freq="1H")
            fallback_df = pd.DataFrame({
                "open": prev_day_close,
                "high": prev_day_close,
                "low": prev_day_close,
                "close": prev_day_close,
                "volume": 0
            }, index=hours)
            df = pd.concat([df, fallback_df])
            df = df.sort_index()

    return df

# 技術指標
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