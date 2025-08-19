import pandas as pd
import numpy as np
import json
import os
import logging
from datetime import datetime
import sys

# === 設定日誌 ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "market_analyst.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === 載入配置 ===
def load_config():
    config_file = "config.json"
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    symbols = cfg.get("symbols", [])
    indicators = cfg.get("indicators", {"MACD":{"fast":12,"slow":26,"signal":9},"RSI":{"period":14}})
    return symbols, indicators

# === 載入資料與策略 ===
def load_data(symbol):
    df_path = os.path.join("data", f"daily_{symbol}.csv")
    strat_path = os.path.join("data", f"strategy_best_{symbol}.json")
    if not os.path.exists(df_path) or not os.path.exists(strat_path):
        logger.warning(f"{symbol} 缺少數據或策略檔案")
        return None, None
    df = pd.read_csv(df_path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Open","High","Low","Close","Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date","Open","High","Low","Close","Volume"]).sort_values("Date")
    with open(strat_path, "r", encoding="utf-8") as f:
        strat = json.load(f)
    return df, strat

# === 指標計算 ===
def calc_macd(df, fast=12, slow=26, signal=9):
    exp1 = df["Close"].ewm(span=fast, adjust=False).mean()
    exp2 = df["Close"].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], sig.iloc[-1]

def calc_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.where(delta>0,0).rolling(period).mean()
    loss = (-delta.where(delta<0,0)).rolling(period).mean()
    rs = gain / loss.replace(0,np.nan)
    rsi = 100 - 100/(1+rs)
    return rsi.iloc[-1] if not rsi.empty else 50

# === 市場分析 ===
def analyze_market(symbol, df, strategy, indicators):
    if df is None or strategy is None:
        return {
            "symbol": symbol,
            "recommendation": "持倉",
            "position_size": 0.0,
            "target_price": None,
            "stop_loss": None,
            "risk_note": "數據不足"
        }
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df)>1 else latest
    pct_change = ((latest["Close"]-prev["Close"])/prev["Close"]*100)
    volume_change = (latest["Volume"]/prev["Volume"]) if prev["Volume"] else 1.0
    macd, sig = calc_macd(df, **indicators.get("MACD", {}))
    rsi = calc_rsi(df, **indicators.get("RSI", {}))
    trend_5d = df["Close"].pct_change(5).iloc[-1]*100 if len(df)>=5 else 0.0

    logger.info(f"{symbol} - 漲跌 {pct_change:.2f}%, 成交量 {volume_change:.2f}x, MACD {macd:.2f}/{sig:.2f}, RSI {rsi:.2f}, 5日趨勢 {trend_5d:.2f}%")

    # 決策
    rec = "持倉"
    pos_size = strategy.get("position_size",0.0)
    if pct_change>1.0 and volume_change>1.2 and macd>sig and rsi>50 and trend_5d>0:
        rec="買入"
        pos_size=min(0.5,0.1+strategy.get("return_pct",0)/20)
    elif pct_change<-1.0 or volume_change<0.8 or macd<sig or rsi<30 or trend_5d<0:
        rec="賣出"
        pos_size=0.0

    target = latest["Close"]*1.02 if rec=="買入" else None
    stop = latest["Close"]*0.98 if rec in ["買入","持倉"] else None
    risk_note=f"漲跌 {pct_change:.2f}%, 成交量 {volume_change:.2f}x, MACD {macd:.2f}/{sig:.2f}, RSI {rsi:.2f}, 5日趨勢 {trend_5d:.2f}%"

    logger.info(f"{symbol} - 建議 {rec}, 倉位 {pos_size:.2f}, 目標價 {target}, 停損 {stop}, 風險 {risk_note}")

    return {
        "symbol": symbol,
        "recommendation": rec,
        "position_size": pos_size,
        "target_price": target,
        "stop_loss": stop,
        "risk_note": risk_note
    }

# === 儲存結果 ===
def save_analysis(analysis):
    path = os.path.join("data", f"market_analysis_{analysis['symbol']}.json")
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis,f,ensure_ascii=False,indent=2)
    logger.info(f"{analysis['symbol']} 分析結果已保存至 {path}")

# === 主流程 ===
def main(run_symbols=None):
    cfg_symbols, indicators = load_config()
    symbols = run_symbols if run_symbols else cfg_symbols
    for symbol in symbols:
        df, strat = load_data(symbol)
        analysis = analyze_market(symbol, df, strat, indicators)
        save_analysis(analysis)

# 支援命令列單一符號
if __name__=="__main__":
    run_syms = sys.argv[1:] if len(sys.argv)>1 else None
    main(run_syms)