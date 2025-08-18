# scripts/data_collector.py
import os
import json
import logging
import time
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

# === 日誌設定 ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("data_collector")

# === 台灣時區 ===
TW_TZ = pytz.timezone("Asia/Taipei")

# === 參數 ===
DATA_DIR = "data"
DAILY_DAYS = 300
HOURLY_DAYS = 14
RETRY_LIMIT = 3

os.makedirs(DATA_DIR, exist_ok=True)


def fetch_with_retry(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """抓取資料，含 retry 機制"""
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            df = yf.download(symbol, interval=interval, period=period, progress=False)
            if df is not None and not df.empty:
                df.index = df.index.tz_localize("UTC").tz_convert(TW_TZ)
                return df
            else:
                raise ValueError("下載回傳空資料")
        except Exception as e:
            logger.warning(f"[{symbol}] 抓取失敗 ({attempt}/{RETRY_LIMIT}) interval={interval}: {e}")
            time.sleep(2 * attempt)
    logger.error(f"[{symbol}] 下載失敗，已超過 {RETRY_LIMIT} 次重試")
    return pd.DataFrame()


def collect_symbol(symbol: str):
    """收集單一 symbol 的日線 + 小時線"""
    logger.info(f"開始收集 {symbol}")

    # === 日線 ===
    daily_df = fetch_with_retry(symbol, "1d", f"{DAILY_DAYS}d")
    if not daily_df.empty:
        daily_path = os.path.join(DATA_DIR, f"daily_{symbol.replace('^', 'INDEX_')}.csv")
        daily_df.to_csv(daily_path)
        logger.info(f"[{symbol}] 已儲存日線 {len(daily_df)} 筆 -> {daily_path}")

    # === 小時線 ===
    hourly_df = fetch_with_retry(symbol, "60m", f"{HOURLY_DAYS}d")
    if not hourly_df.empty:
        hourly_path = os.path.join(DATA_DIR, f"hourly_{symbol.replace('^', 'INDEX_')}.csv")
        hourly_df.to_csv(hourly_path)
        logger.info(f"[{symbol}] 已儲存小時線 {len(hourly_df)} 筆 -> {hourly_path}")


def collect_from_config(config_path="config.json"):
    """讀取 config.json 並收集所有 symbol"""
    if not os.path.exists(config_path):
        logger.error(f"找不到 {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    symbols = config.get("symbols", [])
    logger.info(f"共 {len(symbols)} 個 symbol 需要收集")

    for symbol in symbols:
        collect_symbol(symbol)


if __name__ == "__main__":
    collect_from_config()