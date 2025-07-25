import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ast
import logging

# ===== 日誌設置 =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_price_volume_tw(symbol, start_date=None, end_date=None, min_days=60):
    """
    回傳 (prices: pd.Series, volumes: pd.Series)，日期為 index
    支援 symbol = 'TAIEX'（加權指數）或 '0050'
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
            if len(prices) >= min_days and prices.index.equals(volumes.index):
                logger.info(f"✅ 成功從 {fetcher.__name__} 取得 {symbol}，共 {len(prices)} 筆")
                return prices, volumes
            else:
                logger.warning(f"⚠️ {fetcher.__name__} 返回資料不足或 index 不一致")
        except Exception as e:
            logger.error(f"⚠️ {fetcher.__name__} 錯誤：{e}")

    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料")

# ===== TWSE =====

def fetch_from_twse(symbol, start_date, end_date):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse(start_date, end_date)
    return fetch_stock_from_twse(symbol, start_date, end_date)

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
            if resp.status_code != 200:
                raise RuntimeError(f"TWSE 回應碼錯誤: {resp.status_code}")
            if not resp.text.strip().startswith("{"):
                raise RuntimeError("TWSE 回傳非 JSON 內容")
            data = resp.json()
            tables = data.get("tables", [])
            if not tables or "data" not in tables[0]:
                current_date += timedelta(days=1)
                continue
            for row in tables[0]["data"]:
                if row[0].strip() == "發行量加權股價指數":
                    try:
                        close = float(row[2].replace(",", ""))
                        vol = float(row[4].replace(",", "")) * 1e6
                        prices.append(close)
                        volumes.append(vol)
                        dates.append(current_date)
                    except Exception as e:
                        logger.warning(f"TWSE 行解析錯誤: {e}")
        except Exception as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}")
        current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df[~df.index.duplicated(keep="last")]
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
            raise RuntimeError(f"TWSE {symbol} 無資料")
    except Exception as e:
        raise RuntimeError(f"TWSE {symbol} 錯誤: {e}")

    dates, prices, volumes = [], [], []
    for row in data["data"]:
        try:
            date = pd.to_datetime(row[0].replace("/", "-")).date()
            if date < start_date or date > end_date:
                continue
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", "")) * 1000
            prices.append(close)
            volumes.append(vol)
            dates.append(date)
        except Exception as e:
            logger.warning(f"TWSE 股票資料錯誤: {e}")

    if not prices:
        raise RuntimeError(f"TWSE {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df[~df.index.duplicated(keep="last")]
    return df["Price"], df["Volume"]

# ===== Cnyes =====

def fetch_from_cnyes(symbol, start_date, end_date):
    url_map = {
        "TAIEX": "https://www.cnyes.com/api/v1/charting/index_0000",
        "0050": "https://www.cnyes.com/api/v1/charting/etf_0050"
    }
    url = url_map.get(symbol)
    if not url:
        raise ValueError(f"Cnyes 不支援 symbol: {symbol}")

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    if "data" not in raw or "chart" not in raw["data"]:
        raise RuntimeError("Cnyes 無有效數據")

    data = raw["data"]["chart"]
    dates, prices, volumes = [], [], []
    for x in data:
        try:
            date = datetime.fromtimestamp(x["t"] / 1000).date()
            if date < start_date or date > end_date:
                continue
            prices.append(float(x["c"]))
            volumes.append(float(x["v"]))
            dates.append(date)
        except Exception as e:
            logger.warning(f"Cnyes 資料錯誤: {e}")

    if not prices:
        raise RuntimeError("Cnyes 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df[~df.index.duplicated(keep="last")]
    return df["Price"], df["Volume"]

# ===== PChome =====

def fetch_from_pchome(symbol, start_date, end_date):
    url_map = {
        "TAIEX": "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0",
        "0050": "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    }
    url = url_map.get(symbol)
    if not url:
        raise ValueError(f"PChome 不支援 symbol: {symbol}")

    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        raise RuntimeError("⚠️ 找不到 PChome 資料")

    lines = script_tag.string.splitlines()
    try:
        price_line = next(l for l in lines if "priceList" in l)
        vol_line = next(l for l in lines if "volumeList" in l)
        date_line = next(l for l in lines if "dateList" in l)

        prices = ast.literal_eval(price_line.split("=", 1)[1].strip(" ;"))
        volumes = ast.literal_eval(vol_line.split("=", 1)[1].strip(" ;"))
        dates_raw = ast.literal_eval(date_line.split("=", 1)[1].strip(" ;"))
    except Exception as e:
        raise RuntimeError(f"PChome 解析錯誤: {e}")

    valid_dates, valid_prices, valid_volumes = [], [], []
    for d, p, v in zip(dates_raw, prices, volumes):
        try:
            date = pd.to_datetime(d).date()
            if date < start_date or date > end_date:
                continue
            valid_dates.append(date)
            valid_prices.append(float(p))
            valid_volumes.append(float(v))
        except Exception as e:
            logger.warning(f"PChome 資料錯誤: {e}")

    if not valid_prices:
        raise RuntimeError("PChome 無有效數據")

    df = pd.DataFrame({"Price": valid_prices, "Volume": valid_volumes}, index=pd.to_datetime(valid_dates))
    df = df[~df.index.duplicated(keep="last")]
    return df["Price"], df["Volume"]