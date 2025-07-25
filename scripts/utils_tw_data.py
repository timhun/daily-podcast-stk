import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ast
import logging
import re

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

    for fetcher in [fetch_from_twse, fetch_from_cnyes, fetch_from_pchome]:
        try:
            prices, volumes = fetcher(symbol, start_date, end_date)
            if len(prices) >= min_days and len(volumes) >= min_days and prices.index.equals(volumes.index):
                logger.info(f"✅ 成功從 {fetcher.__name__} 取得 {symbol} 數據，共 {len(prices)} 天")
                return prices, volumes
            else:
                logger.warning(f"⚠️ {fetcher.__name__} 返回資料不足或索引不一致：{len(prices)} 天")
        except Exception as e:
            logger.error(f"⚠️ {fetcher.__name__} 錯誤：{str(e)}")
    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料")



# ===== 第一層：TWSE（證交所歷史資料） =====

def fetch_taiex_from_twse(start_date, end_date):
    prices, volumes, dates = [], [], []
    current_date = start_date
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={date_str}"
        try:
            resp = session.get(url, timeout=10)
            if not resp.text.strip():
                logger.warning(f"TWSE TAIEX {date_str} 回傳空白，跳過")
                current_date += timedelta(days=1)
                continue

            try:
                data = resp.json()
            except ValueError:
                raise RuntimeError(f"TWSE TAIEX {date_str} 回傳非 JSON 格式：{resp.text[:80]}...")

            if "tables" not in data or not data["tables"]:
                logger.warning(f"TWSE TAIEX {date_str} 無 tables 資料")
                current_date += timedelta(days=1)
                continue

            found = False
            for row in data["tables"][0].get("data", []):
                if row[0].strip() == "發行量加權股價指數":
                    try:
                        close = float(row[2].replace(",", ""))
                        vol = float(row[4].replace(",", "")) * 1e6  # 億元 → 元
                        prices.append(close)
                        volumes.append(vol)
                        dates.append(current_date)
                        found = True
                    except Exception as e:
                        logger.warning(f"TWSE TAIEX {date_str} 資料解析錯誤: {e}")
            if not found:
                logger.warning(f"TWSE TAIEX {date_str} 找不到加權指數欄位")
        except Exception as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}")
        current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')].sort_index()
    return df["Price"], df["Volume"]



def fetch_taiex_from_twse(start_date, end_date):
    prices, volumes, dates = [], [], []
    current_date = start_date
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={date_str}"
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "tables" not in data or not data["tables"]:
                logger.warning(f"TWSE TAIEX {date_str} 無 tables 欄位")
                current_date += timedelta(days=1)
                continue
            for row in data["tables"][0].get("data", []):
                if row[0].strip() == "發行量加權股價指數":
                    try:
                        close = float(row[2].replace(",", ""))
                        vol = float(row[4].replace(",", "")) * 1e6  # 億元轉元
                        dates.append(current_date)
                        prices.append(close)
                        volumes.append(vol)
                    except (IndexError, ValueError) as e:
                        logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
        except requests.RequestException as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}")
        current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]  # 移除重複日期
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={symbol}&date={end_date.strftime('%Y%m%d')}&response=json"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data or not data["data"]:
            raise RuntimeError(f"TWSE {symbol} 無數據")
    except requests.RequestException as e:
        raise RuntimeError(f"TWSE {symbol} 請求失敗: {e}")

    dates, prices, volumes = [], [], []
    for row in data["data"]:
        try:
            date_str = row[0].replace("/", "-")
            date = pd.to_datetime(date_str, errors='coerce')
            if pd.isna(date) or date.date() < start_date or date.date() > end_date:
                continue
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", "")) * 1000  # 千股轉股
            dates.append(date)
            prices.append(close)
            volumes.append(vol)
        except (IndexError, ValueError) as e:
            logger.warning(f"TWSE {symbol} 行解析錯誤: {e}")
            continue

    if not prices:
        raise RuntimeError(f"TWSE {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

# ===== 第二層：Cnyes API =====

def fetch_from_cnyes(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v1/charting/index_0000"
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v1/charting/etf_0050"
    else:
        raise ValueError(f"不支持的 symbol: {symbol}")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        if "data" not in raw or "chart" not in raw["data"]:
            raise RuntimeError("Cnyes 無有效 chart 數據")
    except requests.RequestException as e:
        raise RuntimeError(f"Cnyes 請求失敗: {e}")

    data = raw["data"]["chart"]
    dates, prices, volumes = [], [], []
    for x in data:
        try:
            date = datetime.fromtimestamp(x["t"] / 1000).date()
            if date < start_date or date > end_date:
                continue
            dates.append(date)
            prices.append(float(x["c"]))
            volumes.append(float(x["v"]))  # 假設單位為股，需確認
        except (KeyError, ValueError) as e:
            logger.warning(f"Cnyes {symbol} 行解析錯誤: {e}")
            continue

    if not prices:
        raise RuntimeError(f"Cnyes {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]

# ===== 第三層：PChome 網頁爬蟲 =====

def fetch_from_pchome(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0"
    elif symbol == "0050":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    else:
        raise ValueError(f"不支持的 symbol: {symbol}")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        raise RuntimeError(f"PChome {symbol} 請求失敗: {e}")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        raise RuntimeError(f"PChome {symbol} 找不到 dateList 數據")

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
    except (SyntaxError, ValueError) as e:
        raise RuntimeError(f"PChome {symbol} 數據解析錯誤: {e}")

    valid_dates, valid_prices, valid_volumes = [], [], []
    for d, p, v in zip(dates, prices, volumes):
        try:
            date = pd.to_datetime(d, errors='coerce').date()
            if pd.isna(date) or date < start_date or date > end_date:
                continue
            valid_dates.append(date)
            valid_prices.append(float(p))
            valid_volumes.append(float(v))  # 假設單位為股，需確認
        except (ValueError, TypeError) as e:
            logger.warning(f"PChome {symbol} 行解析錯誤: {e}")
            continue

    if not valid_prices:
        raise RuntimeError(f"PChome {symbol} 無有效數據")

    df = pd.DataFrame({"Price": valid_prices, "Volume": valid_volumes}, index=pd.to_datetime(valid_dates))
    df = df.loc[~df.index.duplicated(keep='last')]
    return df["Price"], df["Volume"]