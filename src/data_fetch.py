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
    範例：(('0050.TW', 'Close')) -> '0050.tw_close' or 'close' (視情況)
    我們最終會嘗試找 open/high/low/close/volume 五個欄位（不區分大小寫）
    """
    if isinstance(df.columns, pd.MultiIndex):
        cols = ["_".join([str(x) for x in col]).strip().lower() for col in df.columns.values]
        df.columns = cols
    else:
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # 嘗試映射回 open/high/low/close/volume
    colmap = {}
    want = {"open": None, "high": None, "low": None, "close": None, "volume": None}
    for c in df.columns:
        for w in want.keys():
            if c.endswith("_" + w) or c == w or c.endswith("." + w) or ("_"+w+"_") in c or c.split("_")[-1] == w:
                if want[w] is None:
                    want[w] = c
    # 鬆匹配
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

def fetch_ohlcv(symbol: str, years: int = 3, interval="1d", fallback: bool = False) -> pd.DataFrame:
    """
    下載 OHLCV，並回傳 timezone 設為 Asia/Taipei 下的 DataFrame，
    index 為 timezone-aware DatetimeIndex，欄位為 open/high/low/close/volume（小寫）。
    
    fallback: 若 interval 為小時K且無當天資料，嘗試抓前一天
    """
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=365*years + 60)
    
    df = yf.download(symbol, start=start.date(), end=end.date()+dt.timedelta(days=1),
                     interval=interval, auto_adjust=True, progress=False, threads=True)
    
    if (df is None or df.empty) and fallback and interval.endswith("m"):
        # 小時K fallback：抓前一天資料
        yesterday = end - dt.timedelta(days=1)
        df = yf.download(symbol, start=yesterday.date(), end=end.date(),
                         interval=interval, auto_adjust=True, progress=False, threads=True)
    
    if df is None or df.empty:
        raise RuntimeError("yfinance 下載失敗或無資料")
    
    df = _ensure_cols_flat(df)

    if df.index.tz is None:
        df.index = df.index.tz_localize(dt.timezone.utc)
    df.index = df.index.tz_convert(TAI_TZ)

    return df[["open", "high", "low", "close", "volume"]].dropna()

# 常見技術指標
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