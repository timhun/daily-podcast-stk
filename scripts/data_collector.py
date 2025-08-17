import os
import json
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ====== 工具函式 ======
def normalize_symbol(symbol: str) -> str:
    """
    將股票代號正規化成檔案可用名稱
    - ^TWII -> INDEX_TWII
    - ^GSPC -> INDEX_GSPC
    - 0050.TW -> 0050.TW (不變)
    """
    if symbol.startswith("^"):
        return "INDEX_" + symbol[1:]
    return symbol

def _today_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

# ====== 抓資料 ======
def collect_symbol(symbol: str, use_hourly: bool = True, lookback_days: int = 90):
    interval = "1h" if use_hourly else "1d"
    start = datetime.utcnow() - timedelta(days=lookback_days)
    logger.info(f"下載 {symbol} 資料 interval={interval} start={start.date()}")

    try:
        df = yf.download(symbol, start=start, interval=interval, progress=False)
        if df.empty:
            logger.warning(f"{symbol} 無資料")
            return None
    except Exception as e:
        logger.error(f"{symbol} 抓取失敗: {e}")
        return None

    df.reset_index(inplace=True)
    fname = f"data/{'hourly' if use_hourly else 'daily'}_{normalize_symbol(symbol)}.csv"
    os.makedirs("data", exist_ok=True)
    df.to_csv(fname, index=False)
    logger.info(f"{symbol} 已存檔 -> {fname} 共 {len(df)} 筆")
    return fname

# ====== 從 config.json 讀取 ======
def collect_from_config(config_path="config.json"):
    if not os.path.exists(config_path):
        logger.error(f"找不到設定檔 {config_path}")
        return []

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    symbols = config.get("symbols", [])
    if not symbols:
        logger.warning("config.json 中沒有 symbols 設定")
        return []

    results = []
    for s in symbols:
        results.append(collect_symbol(s, use_hourly=True, lookback_days=120))
        results.append(collect_symbol(s, use_hourly=False, lookback_days=365))
    return [r for r in results if r]