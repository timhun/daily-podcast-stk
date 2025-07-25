import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

# === 第一層：TWSE ===
def fetch_from_twse(symbol):
    if symbol == "TAIEX":
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        table = data["tables"][0]["data"]
        records = []
        for row in table:
            if "發行量加權股價指數" in row[0]:
                close = float(row[1].replace(",", ""))
                change = float(row[2].replace(",", ""))
                date = datetime.today().strftime("%Y-%m-%d")
                records.append((date, close, 0))  # TWSE 無提供日成交量，設為 0
        df = pd.DataFrame(records, columns=["Date", "Price", "Volume"])
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        return df["Price"], df["Volume"]
    elif symbol == "0050":
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo=0050&response=json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data["data"]
        prices, volumes, dates = [], [], []
        for row in rows:
            try:
                date = datetime.strptime(row[0], "%Y/%m/%d")
                close = float(row[6].replace(",", ""))
                volume = float(row[1].replace(",", ""))
                dates.append(date)
                prices.append(close)
                volumes.append(volume)
            except:
                continue
        df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
        return df["Price"].sort_index(), df["Volume"].sort_index()
    else:
        raise ValueError("不支援的 symbol")

# === 第二層：Cnyes API ===
def fetch_from_cnyes(symbol):
    if symbol == "TAIEX":
        url = "https://www.cnyes.com/api/v1/charting/index_0050"
    elif symbol == "0050":
        url = "https://www.cnyes.com/api/v1/charting/etf_0050"
    else:
        raise ValueError("不支援的 symbol")
    resp = requests.get(url)
    chart = resp.json()["data"]["chart"]
    dates = [datetime.fromtimestamp(x["t"] / 1000) for x in chart]
    prices = [x["c"] for x in chart]
    volumes = [x["v"] for x in chart]
    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    return df["Price"].sort_index(), df["Volume"].sort_index()

# === 第三層：PChome 爬蟲 ===
def fetch_from_pchome(symbol):
    if symbol == "TAIEX":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0000/0"
    elif symbol == "0050":
        url = "https://pchome.megatime.com.tw/stock/sidchart/sidchart/trendchart/0050/0"
    else:
        raise ValueError("不支援的 symbol")
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

    df = pd.DataFrame({"Price": prices, "Volume": volumes}, index=pd.to_datetime(dates))
    return df["Price"].sort_index(), df["Volume"].sort_index()
