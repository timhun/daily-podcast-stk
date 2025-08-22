# scripts/strategy_manager.py
import os, json, logging, argparse
import numpy as np
import pandas as pd
from itertools import product
from sklearn.ensemble import RandomForestClassifier

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/strategy_manager.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("strategy")

def load_json(p): 
    with open(p,"r",encoding="utf-8") as f: return json.load(f)

def load_csv_for_symbol(sym):
    path = f"data/daily_{sym.replace('=','').replace('^','').replace('.','_')}.csv"
    return pd.read_csv(path, parse_dates=["Date"])

def buy_and_hold_ret(df):
    close = df["Close"].astype(float)
    return (close.iloc[-1]/close.iloc[0]) - 1.0

def sma_strategy(df, short, long):
    px = df["Close"].astype(float)
    s = px.rolling(short).mean()
    l = px.rolling(long).mean()
    sig = (s > l).astype(int).shift(1).fillna(0)  # 明日持倉
    ret = px.pct_change().fillna(0)
    eq = (sig * ret + (1-sig)*0).add(1).cumprod()
    return eq.iloc[-1] - 1.0

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    down = (-delta.clip(upper=0)).rolling(period).mean()
    rs = up / (down + 1e-9)
    return 100 - (100 /(1+rs))

def rsi_meanrev(df, period=14, low=30, high=70):
    px = df["Close"].astype(float)
    r = rsi(px, period)
    # 低於low買入，高於high賣出；持倉 1/0
    sig = (r < low).astype(int).shift(1).fillna(0)
    ret = px.pct_change().fillna(0)
    eq = (sig * ret).add(1).cumprod()
    return eq.iloc[-1] - 1.0

def rf_classifier(df, n_estimators=100, max_depth=5):
    px = df["Close"].astype(float)
    feat = pd.DataFrame({
        "ret1": px.pct_change(),
        "ret5": px.pct_change(5),
        "sma5": px.rolling(5).mean()/px-1,
        "sma20": px.rolling(20).mean()/px-1,
        "vol5": px.pct_change().rolling(5).std()
    }).dropna()
    y = (px.shift(-1).loc[feat.index] > px.loc[feat.index]).astype(int)  # 明天漲=1
    if len(feat) < 200: 
        return -1e9  # 資料太短不評
    clf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
    split = int(len(feat)*0.7)
    clf.fit(feat.iloc[:split], y.iloc[:split])
    pred = clf.predict_proba(feat.iloc[split:])[:,1]
    # 以0.55為進場門檻
    sig = (pred > 0.55).astype(int)
    ret = pd.Series(px.pct_change().loc[feat.index]).iloc[split:].fillna(0)
    eq = (sig*ret + 0).add(1).cumprod()
    return eq.iloc[-1] - 1.0

def pk_for_symbol(sym, cfg, stratcfg):
    df = load_csv_for_symbol(sym)
    base = buy_and_hold_ret(df)

    best = {"name":"baseline", "params":{}, "return": base}
    # SMA
    for s,l in product(stratcfg["strategies"][0]["params"]["short"], stratcfg["strategies"][0]["params"]["long"]):
        if s>=l: continue
        r = sma_strategy(df, s,l)
        if r>best["return"] and r>base:
            best = {"name":"sma_crossover","params":{"short":s,"long":l},"return":r}
    # RSI
    for p in stratcfg["strategies"][1]["params"]["period"]:
        r = rsi_meanrev(df, period=p)
        if r>best["return"] and r>base:
            best = {"name":"rsi_meanrev","params":{"period":p},"return":r}
    # RF
    for ne in stratcfg["strategies"][2]["params"]["n_estimators"]:
        for md in stratcfg["strategies"][2]["params"]["max_depth"]:
            r = rf_classifier(df, n_estimators=ne, max_depth=md)
            if r>best["return"] and r>base:
                best = {"name":"rf_classifier","params":{"n_estimators":ne,"max_depth":md},"return":r}

    out = f"data/strategy_best_{sym.replace('.','_')}.json"
    with open(out,"w",encoding="utf-8") as f: json.dump(best,f,ensure_ascii=False,indent=2)
    logger.info(f"{sym} best -> {best} (baseline={base:.4f})")

def main():
    cfg = load_json("config.json")
    stratcfg = load_json("strategies.json")
    os.makedirs("data", exist_ok=True)

    for sym in stratcfg["universe"]:
        pk_for_symbol(sym, cfg, stratcfg)

if __name__=="__main__":
    main()

