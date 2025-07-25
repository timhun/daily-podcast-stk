import os
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import json

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
        get_stock_price(symbol, name, mode="daily") for name, symbol in indices.items()
    ]

def get_etf_data_us():
    etfs = {"QQQ": "QQQ", "SPY": "SPY", "IBIT": "IBIT"}
    return ["【美股 ETF】"] + [
        get_stock_price(symbol, name, mode="daily") for name, symbol in etfs.items()
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
        get_stock_price(symbol, name, mode="intraday") for name, symbol in fixed.items()
    ]

def get_hot_stocks_us_from_list():
    path = "hot_stocks_us.json"
    custom = load_json_dict(path)
    if not custom:
        return []
    return ["【自訂美股追蹤清單】"] + [
        get_stock_price(symbol, name, mode="intraday") for name, symbol in custom.items()
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
    try:
        # 第一層：TWSE
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?type=IND&response=json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data["tables"][0]["data"]
        for row in rows:
            if "發行量加權股價指數" in row[0]:
                index = row[1].replace(",", "")
                change = row[2]
                percent = row[3]
                volume = row[4]
                return [f"台股加權指數：{index}（{change}, {percent}），成交值 {volume}，來源：TWSE"]
    except:
        pass

    try:
        # 第二層：Cnyes
        url = "https://www.cnyes.com/twstock/TWS/T00"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        points = soup.select_one(".price")
        change = soup.select_one(".change")
        percent = soup.select_one(".change__percent")
        return [f"台股加權指數：{points.text}（{change.text}, {percent.text}），來源：Cnyes"]
    except:
        pass

    try:
        # 第三層：PChome（非結構化備援）
        url = "https://pchome.megatime.com.tw/stock/sto0/ock0/sidchart/trendchart/0000/0"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            return ["台股加權指數：⚠️ 備援資料來自 PChome（需手動解析）"]
    except:
        pass

    return ["⚠️ 無法取得加權指數資料（TWSE, Cnyes, PChome 均失敗）"]

def fetch_etf_price_from_twse(code):
    try:
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?stockNo={code}&response=json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data.get("data", [])
        if not rows:
            return "⚠️ 無資料"
        last_row = rows[-1]
        return last_row[6]
    except:
        return "⚠️ 錯誤"

def get_etf_data_tw():
    etf_list = {
        "0050": "0050",
        "00631L": "00631L",
        "00878": "00878"
    }
    results = ["【台股 ETF】"]
    for name, code in etf_list.items():
        price = fetch_etf_price_from_twse(code)
        results.append(f"{name}：{price}")
    return results

def get_hot_stocks_tw_by_volume():
    try:
        url = "https://www.twse.com.tw/exchangeReport/MI_INDEX20?response=json&type=ALLBUT0999"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data["data5"][:3]
        results = ["【台股成交量前三大】"]
        for row in rows:
            stock = row[2].strip()
            volume = row[10].strip()
            results.append(f"{stock}（成交量 {volume} 張）")
        return results
    except:
        return ["⚠️ 無法取得成交量排行"]

def get_three_major_investors():
    try:
        today = datetime.now().strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX3?date={today}&response=json"
        resp = requests.get(url)
        data = resp.json()
        rows = data["tables"][0]["data"]
        result = ["【三大法人買賣超（單位：張）】"]
        for row in rows:
            name = row[0].strip()
            buy_sell = row[4].strip()
            result.append(f"{name}：{buy_sell}")
        return result
    except:
        return ["⚠️ 無法取得三大法人資料"]

def get_futures_open_interest():
    try:
        url = "https://www.taifex.com.tw/cht/3/futContractsDate"
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
        return ["⚠️ 無法取得期貨資料"]

def get_tw_margin_balance():
    try:
        url = "https://www.twse.com.tw/exchangeReport/TWT93U?response=json"
        targets = {
            "0050": "0050 元大台灣50",
            "00631L": "00631L 元大台灣50正2",
            "2330": "2330 台積電",
            "大盤": "合計"
        }
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        rows = data["data"]
        results = ["【台股融資融券變化】"]
        for row in rows:
            code = row[0].strip()
            name = row[1].strip()
            full_name = f"{code} {name}"
            if full_name in targets.values():
                margin_change = row[6].replace(",", "").strip()
                short_change = row[10].replace(",", "").strip()
                ratio = row[15].strip()
                short_name = [k for k, v in targets.items() if v == full_name][0]
                results.append(f"{short_name}：融資增 {margin_change} 張、融券增 {short_change} 張、資券比 {ratio}")
        return results
    except:
        return ["⚠️ 無法取得融資融券資料"]

# ===== 主整合入口 =====

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
            get_hot_stocks_tw_by_volume() +
            get_three_major_investors() +
            get_futures_open_interest() +
            get_tw_margin_balance()
        )
    else:
        return "⚠️ 不支援的市場模式"
