# utils_tw_data.py
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
import logging
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil.relativedelta import relativedelta

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 2025 年休市日（參考 TWSE 公告）
HOLIDAYS = [
    "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-28", "2025-04-04", "2025-04-18", "2025-05-01", "2025-06-06", "2025-09-17",
    "2025-10-10"
]
HOLIDAYS = set(d.date() for d in pd.to_datetime(HOLIDAYS))

def is_trading_day(date):
    """檢查是否為交易日（非週末且非假期）"""
    return date.weekday() < 5 and date not in HOLIDAYS

def get_trading_days(start_date, end_date):
    """生成交易日清單，限制不超過當前日期"""
    current_date = datetime.today().date()
    if end_date > current_date:
        logger.warning(f"end_date {end_date} 超過當前日期 {current_date}，調整為 {current_date}")
        end_date = current_date
    dates = pd.date_range(start_date, end_date, freq='B').date
    return [d for d in dates if is_trading_day(d)]

def prepare_df(prices, volumes, min_days, symbol):
    """輔助函式：建立 DataFrame 並嚴格檢查資料完整性"""
    if not isinstance(prices, pd.Series) or not isinstance(volumes, pd.Series):
        raise RuntimeError(f"{symbol} 取得的價格或成交量非 pd.Series")
    if prices.empty or volumes.empty:
        raise RuntimeError(f"{symbol} 取得的價格或成交量為空")
    if not prices.index.equals(volumes.index):
        raise RuntimeError(f"{symbol} 價格及成交量日期索引不一致")
    df = pd.DataFrame({"Price": prices, "Volume": volumes})
    df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]
    if len(df) < min_days:
        raise RuntimeError(f"{symbol} 取得資料少於 {min_days} 天，實得 {len(df)} 天")
    if df["Price"].isna().any() or df["Volume"].isna().any():
        raise RuntimeError(f"{symbol} 資料中有缺失值")
    return df

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
            logger.debug(f"TWSE TAIEX {date_str} 回應: stat={data.get('stat', 'N/A')}, data_len={len(data.get('data', []))}")
            if "data" not in data or not data["data"]:
                logger.warning(f"TWSE TAIEX {date_str} 無資料，stat={data.get('stat', 'N/A')}")
                continue
            for row in data["data"]:
                if len(row) > 10 and isinstance(row[0], str) and row[0].strip() == "發行量加權股價指數":
                    try:
                        date = pd.to_datetime(row[1], format='%Y/%m/%d', errors='coerce').date()
                        if pd.isna(date) or date != current_date:
                            continue
                        close = float(row[8].replace(",", ""))
                        vol = float(row[10].replace(",", "")) * 1e8  # 億元轉新台幣
                        dates.append(date)
                        prices.append(close)
                        volumes.append(vol)
                    except Exception as e:
                        logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
        except requests.RequestException as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}, URL: {resp.url if 'resp' in locals() else url}, Status Code: {resp.status_code if 'resp' in locals() else 'N/A'}")

    if not prices or not volumes:
        raise RuntimeError(f"TWSE TAIEX 無有效數據，請求範圍 {start_date} 至 {end_date}")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    prices, volumes, dates = [], [], []
    session = _twse_session()
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo={symbol}&date={date_str}"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            logger.debug(f"TWSE 股票 {symbol} {date_str} 回應: stat={data.get('stat', 'N/A')}, data_len={len(data.get('data', []))}")
            if "data" not in data or not data["data"]:
                logger.warning(f"TWSE 股票 {symbol} {date_str} 無資料，stat={data.get('stat', 'N/A')}")
                # 用下個月第一天避免跳過
                current_date = (current_date.replace(day=1) + relativedelta(months=1))
                continue
            for row in data["data"]:
                try:
                    date = pd.to_datetime(row[0], format='%Y/%m/%d', errors='coerce').date()
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
            logger.error(f"TWSE 股票 {symbol} {date_str} 請求失敗: {e}, URL: {resp.url if 'resp' in locals() else url}, Status Code: {resp.status_code if 'resp' in locals() else 'N/A'}")
        else:
            current_date = (current_date.replace(day=1) + relativedelta(months=1))

    if not prices or not volumes:
        raise RuntimeError(f"TWSE 股票 {symbol} 無有效數據，請求範圍 {start_date} 至 {end_date}")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

def fetch_from_twse(symbol, start_date, end_date):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse(start_date, end_date)
    else:
        return fetch_stock_from_twse(symbol, start_date, end_date)

def fetch_from_yahoo(symbol, start_date, end_date):
    yf_symbol = "^TWII" if symbol == "TAIEX" else "0050.TW"
    try:
        df = yf.download(yf_symbol, start=start_date, end=end_date + timedelta(days=1), progress=False)
        if df.empty or len(df) < 60:
            raise RuntimeError(f"Yahoo Finance {yf_symbol} 無有效數據或不足 60 天")
        prices = df["Close"]
        volumes = df["Volume"]
        if prices.empty or volumes.empty:
            raise RuntimeError(f"Yahoo Finance {yf_symbol} 資料為空")
        if symbol == "TAIEX":
            volumes = volumes * 2e8
        return prices, volumes
    except Exception as e:
        raise RuntimeError(f"Yahoo Finance 獲取 {yf_symbol} 失敗: {str(e)}")

def get_price_volume_tw_single(symbol, start_date=None, end_date=None, min_days=60):
    # 單段抓取主流程，不做分段。由 get_price_volume_tw 分段調用。
    if end_date is None:
        end_date = datetime.today().date()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()

    current_date = datetime.today().date()
    if end_date > current_date:
        logger.warning(f"end_date {end_date} 為未來日期，調整為 {current_date}")
        end_date = current_date

    cache_file = f"{symbol}_{start_date}_{end_date}_cache.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]
        df = df.loc[(df.index >= start_date) & (df.index <= end_date)]
        if len(df) >= min_days and not df["Price"].isna().any() and not df["Volume"].isna().any():
            logger.info(f"✅ 使用快取數據 {cache_file}，共 {len(df)} 天")
            return df["Price"], df["Volume"]

    try:
        prices, volumes = fetch_from_yahoo(symbol, start_date, end_date)
        df = prepare_df(prices, volumes, min_days, symbol)
        df.to_csv(cache_file)
        logger.info(f"✅ 成功從 Yahoo Finance 取得 {symbol} 數據，共 {len(df)} 天")
        return df["Price"], df["Volume"]
    except Exception as yf_e:
        logger.error(f"⚠️ Yahoo Finance 錯誤：{yf_e}")
        try:
            prices, volumes = fetch_from_twse(symbol, start_date, end_date)
            df = prepare_df(prices, volumes, min_days, symbol)
            df.to_csv(cache_file)
            logger.info(f"✅ 成功從 TWSE 取得 {symbol} 數據，共 {len(df)} 天")
            return df["Price"], df["Volume"]
        except Exception as e:
            logger.error(f"⚠️ TWSE 錯誤：{e}")
            raise RuntimeError(f"Yahoo Finance 無法取得 {symbol} 資料: {str(yf_e)}；TWSE 也失敗: {str(e)}")

def get_price_volume_tw(symbol, start_date=None, end_date=None, min_days=60):
    """
    依月分段呼叫 get_price_volume_tw_single，避免單次大幅區間資料缺失導致取不到資料。
    """
    if end_date is None:
        end_date = datetime.today().date()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()
    if end_date > datetime.today().date():
        logger.warning(f"end_date {end_date} 為未來日期，調整為今天")
        end_date = datetime.today().date()

    prices_all = pd.Series(dtype=float)
    volumes_all = pd.Series(dtype=float)
    current_start = start_date

    while current_start <= end_date:
        current_end = min(current_start + relativedelta(months=1) - timedelta(days=1), end_date)
        try:
            p, v = get_price_volume_tw_single(symbol, current_start, current_end, min_days=1)
            prices_all = pd.concat([prices_all, p])
            volumes_all = pd.concat([volumes_all, v])
        except Exception as e:
            logger.warning(f"分段抓取 {current_start} ~ {current_end} 失敗：{e}")
        current_start = current_end + timedelta(days=1)

    prices_all = prices_all[~prices_all.index.duplicated(keep='last')].sort_index()
    volumes_all = volumes_all[~volumes_all.index.duplicated(keep='last')].sort_index()

    if len(prices_all) < min_days or len(volumes_all) < min_days:
        raise RuntimeError(f"{symbol} 資料少於最低 {min_days} 天，實有 {len(prices_all)} 天")

    df = pd.DataFrame({"Price": prices_all, "Volume": volumes_all})
    df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]

    if df["Price"].isna().any() or df["Volume"].isna().any():
        raise RuntimeError(f"{symbol} 分段資料中有缺失值")

    logger.info(f"✅ 完成分段合併資料，共 {len(df)} 天")
    return df["Price"], df["Volume"]
