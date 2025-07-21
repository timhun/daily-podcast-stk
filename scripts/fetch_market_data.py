# ✅ fetch_market_data.py（已擴充法人與期貨未平倉）

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import time

def get_stock_index_data_us():
    indices = {
        "Dow Jones": "^DJI",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC"
    }
    lines = []
    for name, symbol in indices.items():
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        close = data['Close'].iloc[-1]
        change = data['Close'].iloc[-1] - data['Open'].iloc[-1]
        percent = change / data['Open'].iloc[-1] * 100
        lines.append(f"{name}：{close:.2f}（{change:+.2f}, {percent:+.2f}%）")
    return lines

def get_etf_data_us():
    etfs = {
        "QQQ": "QQQ",
        "SPY": "SPY",
        "IBIT": "IBIT"
    }
    lines = []
    for name, symbol in etfs.items():
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        close = data['Close'].iloc[-1]
        change = data['Close'].iloc[-1] - data['Open'].iloc[-1]
        percent = change / data['Open'].iloc[-1] * 100
        lines.append(f"{name}：{close:.2f}（{change:+.2f}, {percent:+.2f}%）")
    return lines


def get_stock_index_data_tw():
    url = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date=&response=json"
    resp = requests.get(url)
    data = resp.json()
    items = data.get("data", [])
    if items:
        latest = items[-1]
        try:
            # 嘗試取得必要欄位
            close = latest[4]
            change = latest[5]
            return [f"台股加權指數：{close}（漲跌 {change}）"]
        except IndexError:
            return ["⚠️ 無法解析台股加權指數欄位"]
    return ["⚠️ 無法取得台股加權指數"]
    

def get_etf_data_tw():
    urls = {
        "0050": "https://tw.stock.yahoo.com/quote/0050.TW",
        "00631L": "https://tw.stock.yahoo.com/quote/00631L.TW",
        "00713": "https://tw.stock.yahoo.com/quote/00713.TW",
        "00878": "https://tw.stock.yahoo.com/quote/00878.TW"
    }
    results = []
    for name, url in urls.items():
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        try:
            price = soup.select_one("[data-test='qsp-price']").text
            results.append(f"{name}：{price}")
        except:
            results.append(f"{name}：⚠️ 無法取得資料")
    return results

def get_three_major_investors():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX3?date={today}&response=json"
    resp = requests.get(url)
    data = resp.json()
    try:
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
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://www.taifex.com.tw/cht/3/futContractsDate"
    resp = requests.post(url, data={
        'queryType': '1',
        'marketCode': '0',
        'dateaddcnt': '',
        'commodity_id': 'TX',
        'queryDate': datetime.now().strftime("%Y/%m/%d")
    })
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="table_f")
    if not table:
        return ["⚠️ 無法取得期貨未平倉資料"]

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 17 and "外資" in cells[0].text:
            long = cells[8].text.strip()
            short = cells[9].text.strip()
            net = cells[10].text.strip()
            return [f"外資期貨未平倉：多單 {long}、空單 {short}、淨額 {net}"]
    return ["⚠️ 找不到外資期貨資料"]

def get_bitcoin_price():
    ticker = yf.Ticker("BTC-USD")
    data = ticker.history(period="1d")
    close = data['Close'].iloc[-1]
    return f"比特幣：{close:.0f} 美元"

def get_gold_price():
    ticker = yf.Ticker("GC=F")
    data = ticker.history(period="1d")
    close = data['Close'].iloc[-1]
    return f"黃金：{close:.2f} 美元/盎司"

def get_dxy_index():
    ticker = yf.Ticker("DX-Y.NYB")
    data = ticker.history(period="1d")
    close = data['Close'].iloc[-1]
    return f"美元指數：{close:.2f}"

def get_yield_10y():
    ticker = yf.Ticker("^TNX")
    data = ticker.history(period="1d")
    close = data['Close'].iloc[-1] / 100
    return f"美國十年期公債殖利率：{close:.2%}"
