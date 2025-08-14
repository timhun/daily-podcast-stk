# src/data_fetch.py
import pandas as pd, numpy as np, datetime as dt, yfinance as yf
from dateutil import tz

TAI_TZ = tz.gettz("Asia/Taipei")

def fetch_ohlcv(symbol: str, years: int = 3, interval="1d") -> pd.DataFrame:
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=365*years + 60)
    df = yf.download(symbol, start=start.date(), interval=interval, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance 下載失敗或無資料")
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    if df.index.tz is None:
        df.index = df.index.tz_localize(dt.timezone.utc)
    df.index = df.index.tz_convert(TAI_TZ)
    df = df.rename_axis("datetime")
    return df[["open","high","low","close","volume"]].dropna()

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