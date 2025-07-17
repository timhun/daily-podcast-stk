import os
import json
import yfinance as yf

os.makedirs('podcast/latest', exist_ok=True)
data = {}

tickers = {
    '.DJI': '^DJI',
    '.IXIC': '^IXIC',
    '.SPX': '^GSPC',
    'SOX': '^SOX'
}

for k, v in tickers.items():
    t = yf.Ticker(v)
    hist = t.history(period='2d')
    if len(hist) < 2:
        data[k] = {"close": None, "change": None}
    else:
        latest, prev = hist.iloc[-1], hist.iloc[-2]
        data[k] = {
            "close": round(latest['Close'], 2),
            "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
        }

for t in ['QQQ', 'SPY', 'IBIT']:
    tk = yf.Ticker(t)
    hist = tk.history(period='2d')
    if len(hist) < 2:
        data[t] = {"close": None, "change": None}
    else:
        latest, prev = hist.iloc[-1], hist.iloc[-2]
        data[t] = {
            "close": round(latest['Close'], 2),
            "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
        }

btc = yf.Ticker('BTC-USD').history(period='2d')
if len(btc) < 2:
    data['BTC'] = {"close": None, "change": None}
else:
    data['BTC'] = {
        "close": round(btc.iloc[-1]['Close'], 2),
        "change": round((btc.iloc[-1]['Close']-btc.iloc[-2]['Close'])/btc.iloc[-2]['Close']*100, 2)
    }

gold = yf.Ticker('GC=F').history(period='2d')
if len(gold) < 2:
    data['Gold'] = {"close": None, "change": None}
else:
    data['Gold'] = {
        "close": round(gold.iloc[-1]['Close'], 2),
        "change": round((gold.iloc[-1]['Close']-gold.iloc[-2]['Close'])/gold.iloc[-2]['Close']*100, 2)
    }

treasury = yf.Ticker('^TNX').history(period='2d')
if len(treasury) < 2:
    data['US10Y'] = {"close": None, "change": None}
else:
    data['US10Y'] = {
        "close": round(treasury.iloc[-1]['Close'], 2),
        "change": round((treasury.iloc[-1]['Close']-treasury.iloc[-2]['Close'])/treasury.iloc[-2]['Close']*100, 2)
    }

# 熱門股以成交量排序
sp500 = yf.Ticker('^GSPC').constituents if hasattr(yf.Ticker('^GSPC'), 'constituents') else []
if sp500:
    tickers_str = " ".join(sp500[:50])
    top_stocks = yf.download(tickers_str, period="1d", interval="1d")["Volume"].sort_values(ascending=False).head(5)
    data['Top5'] = list(top_stocks.index)
else:
    data['Top5'] = ['AAPL', 'TSLA', 'NVDA', 'AMZN', 'META']

with open('podcast/latest/market.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)