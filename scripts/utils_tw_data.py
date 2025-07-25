import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import ast

def get_price_volume_tw(symbol):
    """
    回傳 (prices: pd.Series, volumes: pd.Series)，日期為 index
    支援 symbol = 'TAIEX'（加權指數）或 '0050'
    """
    for fetcher in [fetch_from_twse, fetch_from_cnyes, fetch_from_pchome]:
        try:
            prices, volumes = fetcher(symbol)
            if len(prices) >= 60 and len(volumes) >= 60:
                return prices, volumes
        except Exception as e:
            print(f"⚠️ 備援來源錯誤：{e}")
    raise RuntimeError(f"❌ 所有備援資料來源皆失敗，無法取得 {symbol} 資料")

# ===== 第一層：TWSE（證交所歷史資料） =====

def fetch_from_twse(symbol):
    if symbol == "TAIEX":
        return fetch_taiex_from_twse()
    else:
        return fetch_stock_from_twse(symbol)

def fetch_taiex_from_twse():
    today = datetime.today().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json&date={today}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = resp.json()

    if "tables" not in data:
        raise RuntimeError("TWSE 沒有 tables 欄位")

    rows = data["tables"][0].get("data", [])
    if not rows:
        raise RuntimeError("TWSE 無加權指數資料")

    dates, prices, volumes = [], [], []
    for row in rows:
        try:
            if row[0].strip() == "發行量加權股價指數":
                close = float(row[2].replace(",", ""))
                vol = float(row[4].replace(",", "")) * 1e6  # 單位：億元轉成元
                dates.append(datetime.today().date())
                prices.append(close)
                volumes.append(vol)
        except Exception as e:
            print(f"⚠️ TWSE row error: {e}")
            continue

    if not prices:
        raise RuntimeError("TWSE 加權指數資料格式錯誤")

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={symbol}&response=json"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = resp.json()

    if "data" not in data:
        raise RuntimeError("TWSE 股票資料錯誤")

    records = data["data"]
    dates, prices, volumes = [], [], []
    for row in records:
        try:
            date_str = row[0].replace("/", "-")
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", "")) * 1000  # 單位：千股
            dates.append(date_str)
            prices.append(close)
            volumes.append(vol)
        except Exception as e:
            print(f"⚠️ TWSE 股票資料錯誤: {e}")
            continue

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    return df["Price"], df["Volume"]

# ===== 第二層：Cnyes API =====

def fetch_from_cnyes(symbol):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v1/charting/index_0000"  # 0000 = TAIEX
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v1/charting/etf_0050"
    else:
        raise ValueError("Unsupported symbol")

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    if "data" not in raw or "chart" not in raw["data"]:
        raise RuntimeError("Cnyes 無資料")

    data = raw["data"]["chart"]
    dates = [datetime.fromtimestamp(x["t"] / 1000).date() for x in data]
    prices = [x["c"] for x in data]
    volumes = [x["v"] for x in data]

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    return df["Price"], df["Volume"]

# ===== 第三層：PChome 網頁爬蟲 =====

def fetch_from_pchome(symbol):
    if symbol == "TAIEX":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0"
    elif symbol == "0050":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    else:
        raise ValueError("Unsupported symbol")

    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        raise RuntimeError("⚠️ 找不到 PChome 資料")

    raw = script_tag.string
    lines = raw.splitlines()

    price_line = [l for l in lines if "priceList" in l][0]
    vol_line = [l for l in lines if "volumeList" in l][0]
    date_line = [l for l in lines if "dateList" in l][0]

    prices = ast.literal_eval(price_line.split("=", 1)[1].strip(" ;"))
    volumes = ast.literal_eval(vol_line.split("=", 1)[1].strip(" ;"))
    dates = ast.literal_eval(date_line.split("=", 1)[1].strip(" ;"))

    df = pd.DataFrame({
        "Price": prices,
        "Volume": volumes
    }, index=pd.to_datetime(dates))
    return df["Price"], df["Volume"]