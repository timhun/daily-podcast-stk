import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ast
import logging

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
            if len(prices) >= min_days and prices.index.equals(volumes.index):
                logger.info(f"✅ 成功從 {fetcher.__name__} 取得 {symbol} 數據，共 {len(prices)} 天")
                return prices, volumes
            else:
                logger.warning(f"⚠️ {fetcher.__name__} 返回資料不足 {min_days} 天或索引不一致")
        except Exception as e:
            logger.error(f"⚠️ {fetcher.__name__} 錯誤：{e}")

    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料")

# ===== 第一層：TWSE =====

def fetch_from_twse(symbol, start_date, end_date):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse(start_date, end_date)
    else:
        return fetch_stock_from_twse(symbol, start_date, end_date)

def fetch_taiex_from_twse(start_date, end_date):
    prices, volumes, dates = [], [], []
    current_date = start_date
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.twse.com.tw/zh/page/trading/exchange/MI_INDEX.html"
    })

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={date_str}"
        try:
            resp = session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                raise RuntimeError(f"TWSE 回應碼錯誤: {resp.status_code}")
            data = resp.json()
            found = False
            for row in data.get("tables", [{}])[0].get("data", []):
                if row[0].strip() == "發行量加權股價指數":
                    try:
                        close = float(row[2].replace(",", ""))
                        vol = float(row[4].replace(",", "")) * 1e6
                        dates.append(current_date)
                        prices.append(close)
                        volumes.append(vol)
                        found = True
                    except Exception as e:
                        logger.warning(f"TWSE TAIEX {date_str} 行解析錯誤: {e}")
            if not found:
                logger.warning(f"TWSE TAIEX {date_str} 無資料行")
        except Exception as e:
            logger.error(f"TWSE TAIEX {date_str} 請求失敗: {e}")
        current_date += timedelta(days=1)

    if not prices:
        raise RuntimeError("TWSE TAIEX 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated()]
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol, start_date, end_date):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={symbol}&date={end_date.strftime('%Y%m%d')}&response=json"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "data" not in data or not data["data"]:
        raise RuntimeError(f"TWSE 股票 {symbol} 無資料")

    dates, prices, volumes = [], [], []
    for row in data["data"]:
        try:
            date = pd.to_datetime(row[0], errors="coerce").date()
            if date < start_date or date > end_date:
                continue
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", "")) * 1000
            dates.append(date)
            prices.append(close)
            volumes.append(vol)
        except Exception as e:
            logger.warning(f"TWSE 股票 {symbol} 行解析錯誤: {e}")

    if not prices:
        raise RuntimeError(f"TWSE 股票 {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated()]
    return df["Price"], df["Volume"]

# ===== 第二層：Cnyes =====

def fetch_from_cnyes(symbol, start_date, end_date):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v1/charting/index_0000"
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v1/charting/etf_0050"
    else:
        raise ValueError(f"Cnyes 不支援 symbol: {symbol}")

    session = requests.Session()
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    data = raw.get("data", {}).get("chart", [])

    dates, prices, volumes = [], [], []
    for x in data:
        try:
            date = datetime.fromtimestamp(x["t"] / 1000).date()
            if date < start_date or date > end_date:
                continue
            prices.append(x["c"])
            volumes.append(x["v"])
            dates.append(date)
        except Exception as e:
            logger.warning(f"Cnyes {symbol} 行解析錯誤: {e}")

    if not prices:
        raise RuntimeError(f"Cnyes {symbol} 無有效數據")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.loc[~df.index.duplicated()]
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
    resp = session.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        raise RuntimeError(f"PChome {symbol} 找不到 script 資料")

    raw = script_tag.string
    lines = raw.splitlines()
    try:
        prices = ast.literal_eval(next(l for l in lines if "priceList" in l).split("=")[1].strip(" ;"))
        volumes = ast.literal_eval(next(l for l in lines if "volumeList" in l).split("=")[1].strip(" ;"))
        dates = ast.literal_eval(next(l for l in lines if "dateList" in l).split("=")[1].strip(" ;"))
    except Exception as e:
        raise RuntimeError(f"PChome {symbol} 解析錯誤: {e}")

    valid_dates, valid_prices, valid_volumes = [], [], []
    for d, p, v in zip(dates, prices, volumes):
        try:
            date = pd.to_datetime(d, errors='coerce').date()
            if date < start_date or date > end_date:
                continue
            valid_dates.append(date)
            valid_prices.append(float(p))
            valid_volumes.append(float(v))
        except Exception as e:
            logger.warning(f"PChome {symbol} 單行解析錯誤: {e}")

    if not valid_prices:
        raise RuntimeError(f"PChome {symbol} 無有效數據")

    df = pd.DataFrame({"Price": valid_prices, "Volume": valid_volumes}, index=pd.to_datetime(valid_dates))
    df = df.loc[~df.index.duplicated()]
    return df["Price"], df["Volume"]