import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ast
import logging
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

    # 檢查快取
    cache_file = f"{symbol}_cache.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if len(df) >= min_days and start_date <= df.index.min().date() <= df.index.max().date() <= end_date:
            logger.info(f"✅ 使用快取數據 {cache_file}，共 {len(df)} 天")
            return df["Price"], df["Volume"]

    errors = []
    for fetcher in [fetch_from_twse, fetch_from_cnyes, fetch_from_pchome]:
        try:
            prices, volumes = fetcher(symbol, start_date, end_date)
            if (
                isinstance(prices, pd.Series)
                and isinstance(volumes, pd.Series)
                and len(prices) >= min_days
                and prices.index.equals(volumes.index)
                and not prices.isna().any()
                and not volumes.isna().any()
            ):
                logger.info(f"✅ 成功從 {fetcher.__name__} 取得 {symbol} 數據，共 {len(prices)} 天")
                df = pd.DataFrame({"Price": prices, "Volume": volumes})
                df.to_csv(cache_file)  # 儲存快取
                return prices, volumes
            else:
                logger.warning(f"⚠️ {fetcher.__name__} 返回資料不足 {min_days} 天或數據無效")
        except Exception as e:
            errors.append(f"{fetcher.__name__}: {str(e)}")
            logger.error(f"⚠️ {fetcher.__name__} 錯誤：{e}")

    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料: {'; '.join(errors)}")

# ===== 第一層：TWSE =====

def fetch_from_twse(symbol, start_date, end_date):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse(start_date, end_date)
    else:
        return fetch_stock_from_twse(symbol, start_date, end_date)

def fetch_taiex_from_twse(start_date, end_date):
    prices, volumes, dates = [], [], []
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[307, 429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.twse.com.tw/zh/page/trading/exchange/MI_INDEX.html"
    })

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        # 使用 CSV 端點以獲取歷史數據（需驗證實際端點）
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX_DAY?date={date_str}&response=csv"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            if resp.headers.get('content-type', '').startswith('text/csv'):
                df = pd.read_csv(resp.content.decode('utf-8'), skiprows=1)
                for _, row in df.iterrows():
                    if row.get('指數名稱', '').strip() == "發行量加權股價指數":
                        try:
                            date = pd.to_datetime(row['日期'], errors='coerce').date()
                            if date < start_date or date > end_date:
                                continue
                            close = float(row['收盤指數'].replace(",", ""))
                            vol = float(row['成交金額'].replace(",", ""))  # 單位：元
                            dates.append(date)
                            prices.append(close)
                            volumes.append(vol)
                        except Exception as e:
                            logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
            else:
                # 回退到 JSON 端點
                url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={date_str}"
                resp = session.get(url, timeout=10, allow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
                found = False
                for row in data.get("tables", [{}])[0].get("data", []):
                    if row[0].strip() == "發行量加權股價指數":
                        try:
                            close = float(row[2].replace(",", ""))
                            vol = float(row[4].replace(",", "")) * 1e6  # 億元轉元
                            dates.append(current_date)
                            prices.append(close)
                            volumes.append(vol)
                            found = True
                        except Exception as e:
                            logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
                if not found:
                    logger.warning(f"TWSE TAIEX {date_str} 無資料行")
        except requests.RequestException as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}, Redirect URL: {resp.url if 'resp' in locals() else 'N/A'}")
        current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    prices, volumes, dates = [], [], []
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[307, 429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.twse.com.tw/zh/page/trading/exchange/STOCK_DAY.html"
    })

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={symbol}&date={date_str}&response=json"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if "data" not in data or not data["data"]:
                current_date += timedelta(days=30)
                continue
            for row in data["data"]:
                try:
                    date = pd.to_datetime(row[0], errors="coerce").date()
                    if pd.isna(date) or date < start_date or date > end_date:
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
        current_date += timedelta(days=30)

    if not prices:
        raise RuntimeError(f"TWSE 股票 {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

# ===== 第二層：Cnyes =====

def fetch_from_cnyes(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v2/charting/index_0000"  # 假設新端點，需驗證
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v2/charting/etf_0050"  # 假設新端點，需驗證
    else:
        raise ValueError(f"Cnyes 不支援 symbol: {symbol}")

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        data = raw.get("data", {}).get("chart", [])
        if not data:
            raise RuntimeError(f"Cnyes {symbol} 無有效數據")
    except requests.RequestException as e:
        raise RuntimeError(f"Cnyes {symbol} 請求失敗: {e}, URL: {url}")

    dates, prices, volumes = [], [], []
    for x in data:
        try:
            date = datetime.fromtimestamp(x["t"] / 1000).date()
            if date < start_date or date > end_date:
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
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        raise RuntimeError(f"PChome {symbol} 請求失敗: {e}, URL: {url}")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        # 嘗試備援解析（假設其他 script 標籤）
        script_tags = soup.find_all("script")
        for tag in script_tags:
            if tag.string and "dateList" in tag.string:
                script_tag = tag
                break
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
            if pd.isna(date) or date < start_date or date > end_date:
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