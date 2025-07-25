# utils_tw_data.py

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

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

# ========== 第一層：TWSE（證交所歷史 CSV） ==========
def fetch_from_twse(symbol):
    name_map = {
        "0050": "0050",
        "TAIEX": "TX"
    }
    if symbol == "TAIEX":
        return fetch_taiex_from_twse()
    else:
        return fetch_stock_from_twse(symbol)

def fetch_taiex_from_twse():
    today = datetime.today()
    end_date = today.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={end_date}&response=json"

    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    data = resp.json()

    records = data["data"]
    dates, prices, volumes = [], [], []
    for row in records:
        try:
            date_str = row[0].replace("/", "-")
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", ""))
            dates.append(date_str)
            prices.append(close)
            volumes.append(vol)
        except:
            continue

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.sort_index()
    return df["Price"], df["Volume"]

def fetch_stock_from_twse(symbol):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={symbol}&response=json"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    data = resp.json()

    records = data["data"]
    dates, prices, volumes = [], [], []
    for row in records:
        try:
            date_str = row[0].replace("/", "-")
            close = float(row[6].replace(",", ""))
            vol = float(row[1].replace(",", ""))
            dates.append(date_str)
            prices.append(close)
            volumes.append(vol)
        except:
            continue

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.sort_index()
    return df["Price"], df["Volume"]

# ========== 第二層：Cnyes API ==========
def fetch_from_cnyes(symbol):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v1/charting/index_0050"
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v1/charting/etf_0050"
    else:
        raise ValueError("Unsupported symbol")

    resp = requests.get(url)
    data = resp.json()["data"]["chart"]

    dates = [datetime.fromtimestamp(x["t"] / 1000).date() for x in data]
    prices = [x["c"] for x in data]
    volumes = [x["v"] for x in data]

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    df = df.sort_index()
    return df["Price"], df["Volume"]

# ========== 第三層：PChome 網頁爬蟲 ==========
def fetch_from_pchome(symbol):
    if symbol == "TAIEX":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0"
    elif symbol == "0050":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    else:
        raise ValueError("Unsupported symbol")

    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")

    script_tag = soup.find("script", string=lambda s: s and "dateList" in s)
    if not script_tag:
        raise RuntimeError("⚠️ 找不到 PChome 資料")

    raw = script_tag.string
    lines = raw.splitlines()
    price_line = [l for l in lines if "priceList" in l][0]
    vol_line = [l for l in lines if "volumeList" in l][0]
    date_line = [l for l in lines if "dateList" in l][0]

    prices = eval(price_line.split("=", 1)[1].strip(" ;"))
    volumes = eval(vol_line.split("=", 1)[1].strip(" ;"))
    dates = eval(date_line.split("=", 1)[1].strip(" ;"))

    df = pd.DataFrame({
        "Price": prices,
        "Volume": volumes
    }, index=pd.to_datetime(dates))
    df = df.sort_index()
    return df["Price"], df["Volume"]