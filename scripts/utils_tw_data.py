# utils_tw_data.py
import pandas as pd
import requests
from datetime import datetime, timedelta
import logging
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2025 年休市日（參考 TWSE 公告，含春節等）
HOLIDAYS = [
    "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-28", "2025-04-04", "2025-05-01", "2025-06-06", "2025-09-17", "2025-10-10"
]
HOLIDAYS = set(pd.to_datetime(HOLIDAYS).date)

def is_trading_day(date):
    """檢查是否為交易日（非週末且非假期）"""
    return date.weekday() < 5 and date not in HOLIDAYS

def get_trading_days(start_date, end_date):
    """生成交易日清單，依賴 HOLIDAYS"""
    dates = pd.date_range(start_date, end_date, freq='B').date
    return [d for d in dates if is_trading_day(d)]

def get_price_volume_tw(symbol, start_date=None, end_date=None, min_days=60):
    """
    回傳 (prices: pd.Series, volumes: pd.Series)，日期為 index
    支援 symbol = 'TAIEX'（加權指數）或 '0050'
    start_date, end_date: 格式 'YYYY-MM-DD' 或 datetime.date，預設為最近 90 天
    min_days: 最小天數要求，預設 60
    """
    if end_date is None:
        end_date = datetime.today().date()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()

    # 防止未來日期
    latest_trading_day = max(get_trading_days(start_date, datetime.today().date()))
    if end_date > latest_trading_day:
        logger.warning(f"end_date {end_date} 為未來日期，調整為最新交易日 {latest_trading_day}")
        end_date = latest_trading_day

    # 檢查快取
    cache_file = f"{symbol}_cache.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]
        df = df.loc[(df.index >= start_date) & (df.index <= end_date)]
        if len(df) >= min_days and not df["Price"].isna().any() and not df["Volume"].isna().any():
            logger.info(f"✅ 使用快取數據 {cache_file}，共 {len(df)} 天")
            return df["Price"], df["Volume"]

    try:
        prices, volumes = fetch_from_twse(symbol, start_date, end_date)
        df = pd.DataFrame({"Price": prices, "Volume": volumes})
        df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]
        if (
            isinstance(prices, pd.Series)
            and isinstance(volumes, pd.Series)
            and len(df) >= min_days
            and prices.index.equals(volumes.index)
            and not prices.isna().any()
            and not volumes.isna().any()
        ):
            df.to_csv(cache_file)
            logger.info(f"✅ 成功從 TWSE 取得 {symbol} 數據，共 {len(df)} 天")
            return df["Price"], df["Volume"]
        else:
            logger.warning(f"⚠️ TWSE 返回資料不足 {min_days} 天或數據無效")
            raise RuntimeError(f"TWSE {symbol} 資料不足或無效")
    except Exception as e:
        logger.error(f"⚠️ TWSE 錯誤：{e}")
        raise RuntimeError(f"TWSE 無法取得 {symbol} 資料: {str(e)}")

def _twse_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.twse.com.tw/zh/statistics/statisticsList",
        "Accept": "application/json"
        # 若需 API 金鑰，取消註解
        # "Authorization": "Bearer YOUR_API_KEY"
    })
    return session

def fetch_from_twse(symbol, start_date, end_date):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse(start_date, end_date)
    else:
        return fetch_stock_from_twse(symbol, start_date, end_date)

def fetch_taiex_from_twse(start_date, end_date):
    prices, volumes, dates = [], [], []
    session = _twse_session()
    trading_days = get_trading_days(start_date, end_date)

    for current_date in trading_days:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if "data" not in data or not data["data"]:
                logger.warning(f"TWSE TAIEX {date_str} 無資料")
                continue
            for row in data["data"]:
                if len(row) > 10 and isinstance(row[0], str) and row[0].strip() == "發行量加權股價指數":
                    try:
                        date = pd.to_datetime(row[1], errors='coerce').date()
                        if pd.isna(date) or date != current_date:
                            continue
                        close = float(row[8].replace(",", ""))
                        vol = float(row[10].replace(",", "")) * 1e6  # 億元轉新台幣
                        dates.append(date)
                        prices.append(close)
                        volumes.append(vol)
                    except Exception as e:
                        logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
        except requests.RequestException as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}, Status Code: {resp.status_code if 'resp' in locals() else 'N/A'}")

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    prices, volumes, dates = [], [], []
    session = _twse_session()
    trading_days = get_trading_days(start_date, end_date)

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo={symbol}&date={date_str}"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if "data" not in data or not data["data"]:
                logger.warning(f"TWSE 股票 {symbol} {date_str} 無資料")
                current_date += timedelta(days=31)
                continue
            for row in data["data"]:
                try:
                    date = pd.to_datetime(row[0], errors='coerce').date()
                    if pd.isna(date) or date < start_date or date > end_date or not is_trading_day(date):
                        continue
                    close = float(row[6].replace(",", ""))
                    vol = float(row[1].replace(",", "")) * 1000  # 千股轉股
                    dates.append(date)
                    prices.append(close)
                    volumes.append(vol)
                except Exception as e:
                    logger.warning(f"TWSE 股票 {symbol} {date_str} 行解析錯誤: {e}")
        except requests.RequestException as e:
            logger.error(f"TWSE 股票 {symbol} {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}, Status Code: {resp.status_code if 'resp' in locals() else 'N/A'}")
        current_date += timedelta(days=31)

    if not prices:
        raise RuntimeError(f"TWSE 股票 {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]