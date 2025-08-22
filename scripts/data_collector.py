# scripts/data_collector.py
import os, json, time, logging, argparse
from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf

os.makedirs("data", exist_ok=True)
logging.basicConfig(filename="logs/data_collector.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("collector")

RETRY = 3
DELAY = 3  # seconds

def load_config():
    with open("config.json","r",encoding="utf-8") as f:
        return json.load(f)

def fetch_and_save(ticker: str, period: str, interval: str, out_prefix: str):
    for i in range(RETRY):
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
            if df is None or df.empty:
                raise ValueError("empty frame")
            df = df.reset_index()
            out = f"data/{out_prefix}_{ticker.replace('=','').replace('^','').replace('.','_')}.csv"
            df.to_csv(out, index=False)
            logger.info(f"{ticker} {interval} saved -> {out} rows={len(df)}")
            return True
        except Exception as e:
            logger.error(f"[{i+1}/{RETRY}] {ticker} {interval} fail: {e}")
            time.sleep(DELAY)
    return False

def main():
    os.makedirs("logs", exist_ok=True)
    cfg = load_config()
    days_daily = cfg["history"]["days_daily"]
    days_hourly = cfg["history"]["days_hourly"]

    # daily
    for t in cfg["symbols"]["us_daily"] + cfg["symbols"]["tw_daily"]:
        fetch_and_save(t, f"{days_daily}d", "1d", "daily")

    # hourly
    for t in cfg["symbols"]["us_hourly"] + cfg["symbols"]["tw_hourly"]:
        fetch_and_save(t, f"{days_hourly}d", "60m", "hourly")

if __name__ == "__main__":
    main()
