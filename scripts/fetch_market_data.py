import yfinance as yf
import requests
import json

data = {}

# 美股指數
tickers = {
    '.DJI': '^DJI',
    '.IXIC': '^IXIC',
    '.SPX': '^GSPC',
    'SOX': '^SOX'
}
for k, v in tickers.items():
    t = yf.Ticker(v)
    hist = t.history(period='2d')
    latest, prev = hist.iloc[-1], hist.iloc[-2]
    data[k] = {
        "close": round(latest['Close'], 2),
        "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
    }

# ETF
for t in ['QQQ', 'SPY', 'IBIT']:
    tk = yf.Ticker(t)
    hist = tk.history(period='2d')
    latest, prev = hist.iloc[-1], hist.iloc[-2]
    data[t] = {
        "close": round(latest['Close'], 2),
        "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
    }

# 比特幣
btc = yf.Ticker('BTC-USD').history(period='2d')
data['BTC'] = {
    "close": round(btc.iloc[-1]['Close'], 2),
    "change": round((btc.iloc[-1]['Close']-btc.iloc[-2]['Close'])/btc.iloc[-2]['Close']*100, 2)
}

# 黃金
gold = yf.Ticker('GC=F').history(period='2d')
data['Gold'] = {
    "close": round(gold.iloc[-1]['Close'], 2),
    "change": round((gold.iloc[-1]['Close']-gold.iloc[-2]['Close'])/gold.iloc[-2]['Close']*100, 2)
}

# 10年美債殖利率
treasury = yf.Ticker('^TNX').history(period='2d')
data['US10Y'] = {
    "close": round(treasury.iloc[-1]['Close'], 2),
    "change": round((treasury.iloc[-1]['Close']-treasury.iloc[-2]['Close'])/treasury.iloc[-2]['Close']*100, 2)
}

# 前五熱門美股（用成交量排名）
sp500 = yf.Ticker('^GSPC').constituents
top_stocks = yf.download(sp500, period="1d", interval="1d").sort_values(('Volume', ''), ascending=False).head(5)
data['Top5'] = top_stocks.index.tolist()

with open('podcast/latest/market.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)