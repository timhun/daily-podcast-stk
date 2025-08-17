import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

LOG_DIR = "logs"
DATA_DIR = "data"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("strategy_manager")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "strategy_manager.log"),
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8"
)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(sh)

# ========== 新增 ==========
def normalize_symbol(symbol: str) -> str:
    """
    把 Yahoo Finance 符號轉換成檔名可用的名稱
    例如：
      - ^TWII -> INDEX_TWII
      - ^GSPC -> INDEX_GSPC
      - 0050.TW -> 0050.TW (不變)
    """
    if symbol.startswith("^"):
        return "INDEX_" + symbol[1:]
    return symbol
# ===========================

def _load_csv(symbol: str, intraday=False) -> pd.DataFrame:
    name = f"hourly_{symbol}.csv" if intraday else f"daily_{symbol}.csv"
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path, parse_dates=["Date"])
    df.sort_values("Date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    for c in ["Open","High","Low","Close","Adj Close","Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Close"]).copy()

def _return(df: pd.DataFrame) -> float:
    if len(df) < 2: return 0.0
    c0, c1 = df["Close"].iloc[0], df["Close"].iloc[-1]
    if c0 == 0 or np.isnan(c0) or np.isnan(c1): return 0.0
    return (c1 - c0) / c0

def _vector_bt(df: pd.DataFrame, signal: pd.Series) -> float:
    rets = df["Close"].pct_change().fillna(0.0)
    strat = (1 + rets * signal.shift(1).fillna(0.0)).prod() - 1
    return float(strat)

def strat_volume_breakout(df: pd.DataFrame) -> Tuple[float, Dict]:
    vol_ma = df["Volume"].rolling(5).mean()
    signal = ((df["Volume"] > 1.5 * vol_ma) & (df["Close"] > df["Close"].shift(1))).astype(int)
    r = _vector_bt(df, signal)
    return r, {"name":"volume_breakout","volume_ma":5,"mult":1.5}

def strat_ma_cross(df: pd.DataFrame) -> Tuple[float, Dict]:
    ma_fast = df["Close"].rolling(10).mean()
    ma_slow = df["Close"].rolling(30).mean()
    signal = (ma_fast > ma_slow).astype(int)
    r = _vector_bt(df, signal)
    return r, {"name":"ma_cross","fast":10,"slow":30}

def strat_rsi(df: pd.DataFrame) -> Tuple[float, Dict]:
    delta = df["Close"].diff()
    up = delta.clip(lower=0).rolling(14).mean()
    dn = (-delta.clip(upper=0)).rolling(14).mean()
    rs = up / (dn.replace(0, np.nan))
    rsi = 100 - 100/(1+rs)
    signal = (rsi < 30).astype(int)
    r = _vector_bt(df, signal)
    return r, {"name":"rsi14_buy_the_dip"}

def model_random_forest(df: pd.DataFrame) -> Tuple[float, Dict, float]:
    feats = pd.DataFrame({
        "ret1": df["Close"].pct_change(),
        "ret5": df["Close"].pct_change(5),
        "vol_z": (df["Volume"] - df["Volume"].rolling(20).mean()) / (df["Volume"].rolling(20).std() + 1e-9),
        "ma10": df["Close"].rolling(10).mean() / (df["Close"].rolling(30).mean() + 1e-9),
    }).fillna(0.0)
    y = (df["Close"].shift(-1) > df["Close"]).astype(int)
    X = feats.values
    yv = y.values
    n = len(df)-1
    if n < 60: 
        return 0.0, {"name":"rf","note":"too_short"}, 0.0
    split = int(n*0.7)
    clf = RandomForestClassifier(n_estimators=200, random_state=42)
    clf.fit(X[:split], yv[:split])
    prob = clf.predict_proba(X[split:-1])[:,1]
    signal = (prob > 0.52).astype(int)
    test_df = df.iloc[split+1:-0] if (split+1)<len(df) else df.iloc[split:]
    rr = _vector_bt(test_df, pd.Series(signal, index=test_df.index))
    acc = accuracy_score(yv[split:-1], (prob>0.5).astype(int)) if len(prob)>0 else 0.0
    return float(rr), {"name":"rf","thresh":0.52,"n_estimators":200,"acc":round(float(acc),3)}, float(acc)

def model_lstm_stub(df: pd.DataFrame) -> Tuple[float, Dict]:
    return 0.0, {"name":"lstm","note":"stub_skipped"}

def _pick_best(cands: Dict[str, Dict], baseline: float) -> Dict:
    good = [(k,v) for k,v in cands.items() if (v["return"] > max(0.0, baseline))]
    if not good:
        return {"winner":"baseline","winner_return":baseline,"details":cands}
    best = max(good, key=lambda kv: kv[1]["return"])
    out = {"winner":best[0],"winner_return":best[1]["return"],"details":cands}
    return out

def run_pk(symbol: str, benchmark: str = None, use_hourly=True) -> Dict:
    sym_file = normalize_symbol(symbol)
    df = _load_csv(sym_file, intraday=use_hourly)

    baseline = 0.0
    if benchmark:
        bench_file = normalize_symbol(benchmark)
        try:
            bdf = _load_csv(bench_file, intraday=use_hourly)
            s = df.set_index("Date")["Close"].pct_change().dropna()
            b = bdf.set_index("Date")["Close"].pct_change().dropna()
            idx = s.index.intersection(b.index)
            if len(idx) > 5:
                baseline = float((1 + b.loc[idx]).prod() - 1)
        except Exception as e:
            logger.warning(f"Baseline {benchmark} 讀取失敗: {e}")

    cands = {}
    for fn, strat in [("volume_breakout", strat_volume_breakout),
                      ("ma_cross", strat_ma_cross),
                      ("rsi14", strat_rsi)]:
        try:
            r, params = strat(df.copy())
            cands[fn] = {"return": float(r), "params": params}
            logger.info(f"{symbol} {fn} return={r:.4f}")
        except Exception as e:
            logger.error(f"{symbol} {fn} 失敗: {e}")

    try:
        rrf, p, acc = model_random_forest(df.copy())
        cands["rf"] = {"return": float(rrf), "params": p}
        logger.info(f"{symbol} RF return={rrf:.4f} acc={acc:.3f}")
    except Exception as e:
        logger.error(f"{symbol} RF 失敗: {e}")

    try:
        rnn, pnn = model_lstm_stub(df.copy())
        cands["lstm"] = {"return": float(rnn), "params": pnn}
    except Exception as e:
        logger.error(f"{symbol} LSTM 失敗: {e}")

    result = _pick_best(cands, baseline)
    result["baseline_return"] = baseline
    result["asof"] = datetime.utcnow().isoformat() + "Z"

    result["signal"] = "hold"
    try:
        if result["winner"] == "volume_breakout":
            vol_ma = df["Volume"].rolling(5).mean()
            last_sig = int((df["Volume"].iloc[-1] > 1.5 * vol_ma.iloc[-1]) and (df["Close"].iloc[-1] > df["Close"].iloc[-2]))
            result["signal"] = "buy" if last_sig else "hold"
            result["price"] = float(df["Close"].iloc[-1])
        elif result["winner"] == "ma_cross":
            ma_fast = df["Close"].rolling(10).mean()
            ma_slow = df["Close"].rolling(30).mean()
            last_sig = int(ma_fast.iloc[-1] > ma_slow.iloc[-1])
            result["signal"] = "buy" if last_sig else "hold"
            result["price"] = float(df["Close"].iloc[-1])
        elif result["winner"] == "rsi14":
            delta = df["Close"].diff()
            up = delta.clip(lower=0).rolling(14).mean()
            dn = (-delta.clip(upper=0)).rolling(14).mean()
            rs = up / (dn.replace(0, np.nan))
            rsi = 100 - 100/(1+rs)
            last_sig = int(rsi.iloc[-1] < 30)
            result["signal"] = "buy" if last_sig else "hold"
            result["price"] = float(df["Close"].iloc[-1])
        elif result["winner"] == "rf":
            result["signal"] = "buy" if result["details"]["rf"]["return"] > baseline else "hold"
            result["price"] = float(df["Close"].iloc[-1])
    except Exception as e:
        logger.warning(f"產生最終訊號失敗: {e}")

    out_path = os.path.join(DATA_DIR, f"strategy_best_{sym_file}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已輸出最佳策略 -> {out_path}")
    return result

if __name__ == "__main__":
    run_pk("0050.TW", benchmark="^TWII")