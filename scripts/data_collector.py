# scripts/data_collector.py
import os
import json
import logging
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

# === 建立 logger ===
def setup_logger(name, log_file, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    fh.setLevel(level)

    eh = logging.FileHandler("logs/error.log", encoding="utf-8")
    eh.setFormatter(formatter)
    eh.setLevel(logging.ERROR)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(level)

    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(eh)
        logger.addHandler(ch)

    return logger

logger = setup_logger("data_collector", "logs/data_collector.log")

# === 工具函式 ===
def load_config(config_path="config.json"):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"載入 config.json 失敗: {e}")
        return {}

def fetch_data(symbol, interval, lookback_days):
    """下載 Yahoo Finance 資料，重試 3 次"""
    for attempt in range(3):
        try:
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            df = yf.download(symbol, start=start_date, interval=interval, progress=False)

            if df is None or df.empty:
                raise ValueError("下載結果為空")

            df.reset_index(inplace=True)
            if "Datetime" in df.columns:
                df.rename(columns={"Datetime": "Date"}, inplace=True)

            # 完全保留 Yahoo 原始日期格式，不轉換、不改格式
            # df["Date"] = pd.to_datetime(df["Date"])  # 可選，用於確保 datetime type

            return df
        except Exception as e:
            logger.warning(f"⚠️ 第 {attempt+1}/3 次抓取 {symbol} ({interval}) 失敗: {e}")
    logger.error(f"❌ 抓取 {symbol} ({interval}) 最終失敗")
    return None

def save_data(df, filepath, max_rows):
    """保存 CSV，只保留指定筆數"""
    try:
        df = df.tail(max_rows)
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info(f"✅ 已更新 {filepath} ({len(df)} 筆) | 最後一筆: {df.iloc[-1]['Date']} Close={df.iloc[-1]['Close']}")
    except Exception as e:
        logger.error(f"❌ 保存 {filepath} 失敗: {e}")

# === 主程式 ===
def main():
    config = load_config()
    if not config or "symbols" not in config:
        logger.error("❌ config.json 缺少 symbols 設定")
        return

    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    for symbol in config["symbols"]:
        logger.info(f"📥 處理 {symbol}")

        # 日線，保留 300 天
        daily = fetch_data(symbol, "1d", 365)
        if daily is not None:
            save_data(daily, f"data/daily_{symbol}.csv", 300)

        # 小時線，保留最近 14 天資料
        hourly = fetch_data(symbol, "60m", 30)
        if hourly is not None:
            save_data(hourly, f"data/hourly_{symbol}.csv", 14 * 7)  # 一天約7筆交易小時

if __name__ == "__main__":
    logger.info("🚀 Data Collector 開始執行")
    main()
    logger.info("🏁 Data Collector 結束")