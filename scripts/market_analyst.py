import os, json, logging
import pandas as pd
import numpy as np

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/market_analyst.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("analyst")

def macd(px, fast=12, slow=26, sig=9):
    ema_fast = px.ewm(span=fast, adjust=False).mean()
    ema_slow = px.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal = macd_line.ewm(span=sig, adjust=False).mean()
    hist = macd_line - signal
    return macd_line, signal, hist

def analyze(sym):
    df = pd.read_csv(f"data/daily_{sym.replace('=','').replace('^','').replace('.','_')}.csv", parse_dates=["Date"])
    px = df["Close"].astype(float)
    macd_l, sig, hist = macd(px)
    trend = "上升" if macd_l.iloc[-1] > sig.iloc[-1] else "下降"

    best_path = f"data/strategy_best_{sym.replace('.','_')}.json"
    best = json.load(open(best_path,"r",encoding="utf-8")) if os.path.exists(best_path) else {"name":"baseline","return":0}

    advice = "偏多格局，逢回分批" if trend=="上升" else "偏保守，觀察支撐壓力"
    risk = []
    if hist.iloc[-1] < 0 and trend=="下降": risk.append("動能轉弱")
    if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1]*1.5: risk.append("量能異常")
    result = {
        "symbol": sym,
        "last_close": float(px.iloc[-1]),
        "trend": trend,
        "best_strategy": best,
        "advice": advice,
        "risk_flags": risk[-3:],
    }
    out = f"data/market_analysis_{sym.replace('.','_')}.json"
    json.dump(result, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    logger.info(f"{sym} analysis saved -> {out}")

def main():
    # 針對 0050、QQQ 基本盤
    for sym in ["0050.TW","QQQ"]:
        analyze(sym)

if __name__=="__main__":
    main()
