import os
import datetime
import yfinance as yf
import requests

def get_stock_index_data_us():
    tickers = {
        "^DJI": "道瓊指數",
        "^GSPC": "標普500",
        "^IXIC": "那斯達克"
    }
    summary = []
    for symbol, name in tickers.items():
        data = yf.Ticker(symbol)
        price = data.history(period="1d")
        if price.empty:
            continue
        last = price["Close"].iloc[-1]
        summary.append(f"{name}: {last:.2f}")
    return summary

def get_stock_index_data_tw():
    tickers = {
        "^TWII": "加權指數",
        "^TWOII": "櫃買指數"
    }
    summary = []
    for symbol, name in tickers.items():
        data = yf.Ticker(symbol)
        price = data.history(period="1d")
        if price.empty:
            continue
        last = price["Close"].iloc[-1]
        summary.append(f"{name}: {last:.2f}")
    return summary

def get_etf_data_us():
    tickers = {
        "QQQ": "QQQ",
        "SPY": "SPY",
        "IBIT": "IBIT"
    }
    summary = []
    for symbol, name in tickers.items():
        data = yf.Ticker(symbol)
        price = data.history(period="1d")
        if price.empty:
            continue
        last = price["Close"].iloc[-1]
        summary.append(f"{name}: {last:.2f}")
    return summary

def get_etf_data_tw():
    tickers = {
        "0050.TW": "0050 台灣50",
        "00878.TW": "00878 高股息",
        "006208.TW": "富邦台50",
        "00631L.TW": "00631L 元大台灣50正2"
    }
    summary = []
    for symbol, name in tickers.items():
        data = yf.Ticker(symbol)
        price = data.history(period="1d")
        if price.empty:
            continue
        last = price["Close"].iloc[-1]
        summary.append(f"{name}: {last:.2f}")
    return summary

def get_bitcoin_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        data = r.json()
        price = data["bitcoin"]["usd"]
        return f"比特幣: ${price}"
    except:
        return "比特幣價格讀取失敗"

def get_gold_price():
    try:
        r = requests.get("https://data-asg.goldprice.org/dbXRates/USD")
        data = r.json()
        price = data["items"][0]["xauPrice"]
        return f"黃金價格: ${price:.2f}"
    except:
        return "黃金價格讀取失敗"

def get_dxy_index():
    try:
        data = yf.Ticker("DX-Y.NYB").history(period="1d")
        if data.empty:
            return "美元指數讀取失敗"
        last = data["Close"].iloc[-1]
        return f"美元指數 DXY: {last:.2f}"
    except:
        return "美元指數讀取失敗"

def get_yield_10y():
    try:
        data = yf.Ticker("^TNX").history(period="1d")
        if data.empty:
            return "10年期公債殖利率讀取失敗"
        last = data["Close"].iloc[-1]
        return f"美國十年期公債殖利率: {last:.2f}%"
    except:
        return "10年期公債殖利率讀取失敗"

def get_stock_index_data(mode="us"):
    if mode == "tw":
        return get_stock_index_data_tw()
    else:
        return get_stock_index_data_us()

def get_etf_data(mode="us"):
    if mode == "tw":
        return get_etf_data_tw()
    else:
        return get_etf_data_us()