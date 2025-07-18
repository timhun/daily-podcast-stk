import yfinance as yf
import requests

def get_stock_index_data():
    symbols = {
        "^DJI": "道瓊工業指數",
        "^IXIC": "NASDAQ 指數",
        "^GSPC": "S&P500 指數",
        "^SOX": "費城半導體指數"
    }
    data = []
    for symbol, name in symbols.items():
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) < 2:
            continue
        today = hist.iloc[-1]
        prev = hist.iloc[-2]
        change = today["Close"] - prev["Close"]
        percent = (change / prev["Close"]) * 100
        data.append(f"{name} 收報 {today['Close']:.2f}，漲跌幅 {change:+.2f}（{percent:+.2f}%）")
    return data

def get_etf_data():
    symbols = {
        "QQQ": "QQQ",
        "SPY": "SPY",
        "IBIT": "IBIT（BlackRock 比特幣 ETF）"
    }
    data = []
    for symbol, name in symbols.items():
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) < 2:
            continue
        today = hist.iloc[-1]
        prev = hist.iloc[-2]
        change = today["Close"] - prev["Close"]
        percent = (change / prev["Close"]) * 100
        data.append(f"{name} 收盤 {today['Close']:.2f}（{percent:+.2f}%）")
    return data

def get_bitcoin_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    r = requests.get(url)
    if r.status_code == 200:
        price = r.json()["bitcoin"]["usd"]
        return f"比特幣最新報價約 {price:,.0f} 美元"
    return "比特幣資料無法取得"

def get_gold_price():
    ticker = yf.Ticker("GC=F")
    hist = ticker.history(period="2d")
    if len(hist) < 2:
        return "黃金資料不足"
    today = hist.iloc[-1]
    prev = hist.iloc[-2]
    change = today["Close"] - prev["Close"]
    percent = (change / prev["Close"]) * 100
    return f"黃金價格每盎司 {today['Close']:.2f} 美元（{percent:+.2f}%）"

def get_dxy_index():
    ticker = yf.Ticker("DX-Y.NYB")
    hist = ticker.history(period="2d")
    if len(hist) < 2:
        return "美元指數資料不足"
    today = hist.iloc[-1]
    prev = hist.iloc[-2]
    change = today["Close"] - prev["Close"]
    percent = (change / prev["Close"]) * 100
    return f"美元指數目前 {today['Close']:.2f}（{percent:+.2f}%）"

def get_yield_10y():
    ticker = yf.Ticker("^TNX")
    hist = ticker.history(period="2d")
    if len(hist) < 2:
        return "10 年期美債殖利率資料不足"
    today = hist.iloc[-1]
    return f"美國 10 年期公債殖利率為 {today['Close']:.2f}%"