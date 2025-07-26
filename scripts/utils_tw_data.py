import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ast
import logging
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 台灣股市休市日（2025年）
HOLIDAYS = [
    "2025-01-01", "2025-02-28", "2025-04-04", "2025-05-01", "2025-06-06",
    "2025-09-17", "2025-10-10"
]
HOLIDAYS = set(pd.to_datetime(HOLIDAYS).date)

def is_trading_day(date):
    """檢查是否為交易日（非週末且非假期）"""
    return date.weekday() < 5 and date not in HOLIDAYS

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
    if end_date > datetime.today().date():
        logger.warning(f"end_date {end_date} 為未來日期，調整為今天 {datetime.today().date()}")
        end_date = datetime.today().date()

    # 檢查快取
    cache_file = f"{symbol}_cache.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        df = df[df.index.to_series().apply(lambda d: is_trading_day(d.date()))]
        df = df.loc[(df.index >= start_date) & (df.index <= end_date)]
        if len(df) >= min_days and not df["Price"].isna().any() and not df["Volume"].isna().any():
            logger.info(f"✅ 使用快取數據 {cache_file}，共 {len(df)} 天")
            return df["Price"], df["Volume"]

    errors = []
    for fetcher in [fetch_from_twse, fetch_from_cnyes, fetch_from_pchome]:
        try:
            prices, volumes = fetcher(symbol, start_date, end_date)
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
                logger.info(f"✅ 成功從 {fetcher.__name__} 取得 {symbol} 數據，共 {len(df)} 天")
                return df["Price"], df["Volume"]
            else:
                logger.warning(f"⚠️ {fetcher.__name__} 返回資料不足 {min_days} 天或數據無效")
        except Exception as e:
            errors.append(f"{fetcher.__name__}: {str(e)}")
            logger.error(f"⚠️ {fetcher.__name__} 錯誤：{e}")

    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料: {'; '.join(errors)}")

# ===== 第一層：TWSE =====

def _twse_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[307, 429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.twse.com.tw/zh/statistics/statisticsList",
        "Accept": "application/json"
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
    current_date = start_date
    while current_date <= end_date:
        if not is_trading_day(current_date):
            current_date += timedelta(days=1)
            continue
        date_str = current_date.strftime("%Y%m%d")
        # 使用批量歷史數據端點（需驗證）
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if "data" not in data or not data["data"]:
                logger.warning(f"TWSE TAIEX {date_str} 無資料")
                current_date += timedelta(days=1)
                continue
            for row in data["data"]:
                if row[0].strip() == "發行量加權股價指數":
                    try:
                        date = pd.to_datetime(row[1], errors='coerce').date()
                        if pd.isna(date) or date < start_date or date > end_date or not is_trading_day(date):
                            continue
                        close = float(row[8].replace(",", ""))  # 收盤價，需驗證欄位
                        vol = float(row[10].replace(",", "")) * 1e6  # 成交金額（億元轉元）
                        dates.append(date)
                        prices.append(close)
                        volumes.append(vol)
                    except Exception as e:
                        logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
        except requests.RequestException as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}")
        current_date += timedelta(days=1)

    if not prices:
        # 嘗試備援端點（單日 MI_INDEX）
        current_date = start_date
        while current_date <= end_date:
            if not is_trading_day(current_date):
                current_date += timedelta(days=1)
                continue
            date_str = current_date.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={date_str}"
            try:
                resp = session.get(url, timeout=10, allow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
                for row in data.get("tables", [{}])[0].get("data", []):
                    if row[0].strip() == "發行量加權股價指數":
                        try:
                            close = float(row[2].replace(",", ""))
                            vol = float(row[4].replace(",", "")) * 1e6
                            prices.append(close)
                            volumes.append(vol)
                            dates.append(current_date)
                        except Exception as e:
                            logger.warning(f"TWSE TAIEX 備援 {date_str} 行解析錯誤: {e}")
            except requests.RequestException as e:
                logger.error(f"TWSE TAIEX 備援 {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}")
            current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    prices, volumes, dates = [], [], []
    session = _twse_session()
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        if not is_trading_day(current_date):
            current_date += timedelta(days=1)
            continue
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
            logger.error(f"TWSE 股票 {symbol} {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}")
        current_date += timedelta(days=31)

    if not prices:
        raise RuntimeError(f"TWSE 股票 {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

# ===== 第二層：Cnyes =====

def fetch_from_cnyes(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v3/market/index/history"  # 假設新端點，需驗證
        params = {"symbol": "TAIEX", "start": start_date.strftime("%Y%m%d"), "end": end_date.strftime("%Y%m%d")}
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v3/market/etf/history"  # 假設新端點，需驗證
        params = {"symbol": "0050", "start": start_date.strftime("%Y%m%d"), "end": end_date.strftime("%Y%m%d")}
    else:
        raise ValueError(f"Cnyes 不支援 symbol: {symbol}")

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    })

    try:
        resp = session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        data = raw.get("data", {}).get("history", [])  # 假設結構，需驗證
        if not data:
            raise RuntimeError(f"Cnyes {symbol} 無有效數據")
    except requests.RequestException as e:
        raise RuntimeError(f"Cnyes {symbol} 請求失敗: {e}, URL: {url}")

    dates, prices, volumes = [], [], []
    for x in data:
        try:
            date = datetime.fromtimestamp(x["t"] / 1000).date()
            if date < start_date or date > end_date or not is_trading_day(date):
                continue
            prices.append(float(x["c"]))
            volumes.append(float(x["v"]))  # 假設單位為股，需驗證
            dates.append(date)
        except Exception as e:
            logger.warning(f"Cnyes {symbol} 行解析錯誤: {e}")

    if not prices:
        raise RuntimeError(f"Cnyes {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

# ===== 第三層：PChome =====

def fetch_from_pchome(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0"
    elif symbol == "0050":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    else:
        raise ValueError(f"PChome 不支援 symbol: {symbol}")

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html"
    })

    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"PChome {symbol} 靜態請求失敗: {e}, 嘗試動態解析")
        soup = None

    if soup:
        script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
        if not script_tag:
            script_tags = soup.find_all("script")
            for tag in script_tags:
                if tag.string and "dateList" in tag.string:
                    script_tag = tag
                    break

    if not soup or not script_tag:
        logger.info(f"PChome {symbol} 使用 Selenium 動態解析")
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(url)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
            if not script_tag:
                script_tags = soup.find_all("script")
                for tag in script_tags:
                    if tag.string and "dateList" in tag.string:
                        script_tag = tag
                        break
            driver.quit()
        except Exception as e:
            driver.quit()
            raise RuntimeError(f"PChome {symbol} Selenium 解析失敗: {e}")

    if not script_tag:
        raise RuntimeError(f"PChome {symbol} 找不到 script 資料")

    raw = script_tag.string
    lines = raw.splitlines()
    price_line = next((l for l in lines if "priceList" in l), None)
    vol_line = next((l for l in lines if "volumeList" in l), None)
    date_line = next((l for l in lines if "dateList" in l), None)

    if not (price_line and vol_line and date_line):
        raise RuntimeError(f"PChome {symbol} 缺少必要數據欄位")

    try:
        prices = ast.literal_eval(price_line.split("=", 1)[1].strip(" ;"))
        volumes = ast.literal_eval(vol_line.split("=", 1)[1].strip(" ;"))
        dates = ast.literal_eval(date_line.split("=", 1)[1].strip(" ;"))
    except Exception as e:
        raise RuntimeError(f"PChome {symbol} 解析錯誤: {e}")

    valid_dates, valid_prices, valid_volumes = [], [], []
    for d, p, v in zip(dates, prices, volumes):
        try:
            date = pd.to_datetime(d, errors='coerce').date()
            if pd.isna(date) or date < start_date or date > end_date or not is_trading_day(date):
                continue
            valid_dates.append(date)
            valid_prices.append(float(p))
            valid_volumes.append(float(v))  # 假設單位為股，需驗證
        except Exception as e:
            logger.warning(f"PChome {symbol} 單行解析錯誤: {e}")

    if not valid_prices:
        raise RuntimeError(f"PChome {symbol} 無有效數據")

    df = pd.DataFrame({"Price": valid_prices, "Volume": valid_volumes}, index=pd.to_datetime(valid_dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]