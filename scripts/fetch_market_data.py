# ✅ fetch_market_data.py（更新後）
import requests
import yfinance as yf
from bs4 import BeautifulSoup

def get_stock_index_data_us():
    # 使用 Yahoo Finance
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
        date, open_, high, low, close, change, volume = latest[:7]
        return [
            f"台股加權指數：{close}（漲跌 {change}）",
        ]
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
            price = soup.select_one("[data-test='qsp-price"]").text
            results.append(f"{name}：{price}")
        except:
            results.append(f"{name}：⚠️ 無法取得資料")
    return results

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


# ✅ generate_script_kimi.py 中擷取邏輯更新如下：
#（插入在行前面，替代原 get_stock_index_data 與 get_etf_data）

from fetch_market_data import (
    get_stock_index_data_us,
    get_etf_data_us,
    get_stock_index_data_tw,
    get_etf_data_tw,
    get_bitcoin_price,
    get_gold_price,
    get_dxy_index,
    get_yield_10y
)

if PODCAST_MODE == "tw":
    stock_summary = "\n".join(get_stock_index_data_tw())
    etf_summary = "\n".join(get_etf_data_tw())
else:
    stock_summary = "\n".join(get_stock_index_data_us())
    etf_summary = "\n".join(get_etf_data_us())