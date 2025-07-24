import os
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import json

# ===== 通用工具 =====

def get_stock_price(symbol, name=None, mode="intraday"):
    try:
        ticker = yf.Ticker(symbol)
        if mode == "daily":
            data = ticker.history(period="2d", interval="1d")
            if data.empty or len(data) < 2:
                return f"{name or symbol}：⚠️ 無法取得日線資料"
            latest = data.iloc[-1]
            open_ = data.iloc[-2]["Close"]
        else:
            data = ticker.history(period="1d", interval="1m")
            if data.empty:
                return f"{name or symbol}：⚠️ 無法取得即時資料"
            latest = data.iloc[-1]
            open_ = data["Open"].iloc[0]

        close = latest["Close"]
        change = close - open_
        percent = change / open_ * 100
        return f"{name or symbol}：{close:.2f}（{change:+.2f}, {percent:+.2f}%）"
    except:
        return f"{name or symbol}：⚠️ 發生錯誤"

def load_json_dict(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===== 美股區 =====

def get_stock_index_data_us():
    indices = {
        "道瓊指數": "^DJI",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "費城半導體": "^SOX"
    }
    return ["【美股主要指數】"] + [
        get_stock_price(symbol, name, mode="daily")
        for name, symbol in indices.items()
    ]

def get_etf_data_us():
    etfs = {
        "QQQ": "QQQ",
        "SPY": "SPY",
        "IBIT": "IBIT"
    }
    return ["【美股 ETF】"] + [
        get_stock_price(symbol, name, mode="daily")
        for name, symbol in etfs.items()
    ]

def get_hot_stocks_us():
    fixed = {
        "輝達（NVDA）": "NVDA",
        "蘋果（AAPL）": "AAPL",
        "特斯拉（TSLA）": "TSLA",
        "亞馬遜（AMZN）": "AMZN",
        "微軟（MSFT）": "MSFT"
    }
    return ["【美股熱門個股】"] + [
        get_stock_price(symbol, name, mode="intraday")
        for name, symbol in fixed.items()
    ]

def get_hot_stocks_us_from_list():
    path = "hot_stocks_us.json"
    custom = load_json_dict(path)
    if not custom:
        return []
    return ["【自訂美股追蹤清單】"] + [
        get_stock_price(symbol, name, mode="intraday")
        for name, symbol in custom.items()
    ]

def get_bitcoin_price():
    return get_stock_price("BTC-USD", "比特幣", mode="intraday")

def get_gold_price():
    return get_stock_price("GC=F", "黃金", mode="daily")

def get_dxy_index():
    return get_stock_price("DX-Y.NYB", "美元指數", mode="daily")

def get_yield_10y():
    try:
        data = yf.Ticker("^TNX").history(period="2d", interval="1d")
        close = data["Close"].iloc[-1] / 100
        return f"美國十年期公債殖利率：{close:.2%}"
    except:
        return "⚠️ 無法取得十年期殖利率"

# ===== 台股區 =====

def get_stock_index_data_tw():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={today}&type=IND&response=json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        table = data.get("tables", [])[0]
        rows = table.get("data", [])
        for row in rows:
            if "發行量加權股價指數" in row[0]:
                index = row[1].replace(",", "")
                change = row[2].replace(",", "")
                percent = row[3].replace(",", "")
                volume = row[4].replace(",", "")
                return [f"台股加權指數：{float(index):,.2f}（{float(change):+.2f}, {float(percent):+.2f}%），成交值 {float(volume):,.0f} 億"]
        return ["⚠️ 找不到台股加權指數資料"]
    except Exception as e:
        return [f"⚠️ 擷取台股指數失敗：{e}"]


def get_etf_data_tw():
    urls = {
        "0050": "https://tw.stock.yahoo.com/quote/0050.TW",
        "00631L": "https://tw.stock.yahoo.com/quote/00631L.TW",
        "00713": "https://tw.stock.yahoo.com/quote/00713.TW",
        "00878": "https://tw.stock.yahoo.com/quote/00878.TW"
    }
    results = ["【台股 ETF】"]
    for name, url in urls.items():
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
            if not tag:
                tag = soup.find("span", {"class": "Fz(32px)"})
            price = tag.text.strip() if tag else "N/A"
            results.append(f"{name}：{price}")
        except:
            results.append(f"{name}：⚠️ 無法取得資料")
    return results

def get_hot_stocks_tw_from_list():
    path = "hot_stocks_tw.json"
    custom = load_json_dict(path)
    if not custom:
        return []
    results = ["【自訂台股追蹤清單】"]
    for name, url in custom.items():
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("fin-streamer", {"data-field": "regularMarketPrice"})
            if not tag:
                tag = soup.find("span", {"class": "Fz(32px)"})
            price = tag.text.strip() if tag else "N/A"
            results.append(f"{name}：{price}")
        except:
            results.append(f"{name}：⚠️ 無法取得資料")
    return results

def get_hot_stocks_tw_by_volume():
    url = "https://www.twse.com.tw/exchangeReport/MI_INDEX20?response=json&type=ALLBUT0999"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data["data5"][:5]
        results = ["【台股成交量前五】"]
        for row in rows:
            stock = row[2]
            volume = row[10]
            results.append(f"{stock}（成交量 {volume} 張）")
        return results
    except:
        return ["⚠️ 無法取得成交量排行榜"]

def get_three_major_investors():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX3?date={today}&response=json"
    try:
        resp = requests.get(url)
        data = resp.json()
        rows = data['tables'][0]['data']
        result = ["【三大法人買賣超（單位：張）】"]
        for row in rows:
            name = row[0].strip()
            buy_sell = row[4].strip()
            result.append(f"{name}：{buy_sell}")
        return result
    except:
        return ["⚠️ 無法取得三大法人資料"]

def get_futures_open_interest():
    url = f"https://www.taifex.com.tw/cht/3/futContractsDate"
    try:
        resp = requests.post(url, data={
            'queryType': '1',
            'marketCode': '0',
            'dateaddcnt': '',
            'commodity_id': 'TX',
            'queryDate': datetime.now().strftime("%Y/%m/%d")
        }, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table_f")
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 17 and "外資" in cells[0].text:
                long = cells[8].text.strip()
                short = cells[9].text.strip()
                net = cells[10].text.strip()
                return [f"外資期貨未平倉：多單 {long}、空單 {short}、淨額 {net}"]
        return ["⚠️ 找不到外資期貨資料"]
    except:
        return ["⚠️ 無法取得期貨未平倉資料"]

# ===== 統一輸出 =====

def get_market_summary(mode: str) -> str:
    if mode == "us":
        return "\n".join(
            get_stock_index_data_us() +
            get_etf_data_us() +
            get_hot_stocks_us() +
            get_hot_stocks_us_from_list() +
            [
                get_bitcoin_price(),
                get_gold_price(),
                get_dxy_index(),
                get_yield_10y()
            ]
        )
    elif mode == "tw":
        return "\n".join(
            get_stock_index_data_tw() +
            get_etf_data_tw() +
            get_hot_stocks_tw_from_list() +
            get_hot_stocks_tw_by_volume() +
            get_three_major_investors() +
            get_futures_open_interest()
        )
    else:
        return "⚠️ 不支援的市場模式"
