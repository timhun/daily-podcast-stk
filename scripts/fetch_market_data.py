import yfinance as yf
import json

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
        print(f"警告：{k} 沒有足夠的資料")
        data[k] = {"close": None, "change": None}
        continue
    latest, prev = hist.iloc[-1], hist.iloc[-2]
    data[k] = {
        "close": round(latest['Close'], 2),
        "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
    }

for t in ['QQQ', 'SPY', 'IBIT']:
    tk = yf.Ticker(t)
    hist = tk.history(period='2d')
    if len(hist) < 2:
        print(f"警告：{t} 沒有足夠的資料")
        data[t] = {"close": None, "change": None}
        continue
    latest, prev = hist.iloc[-1], hist.iloc[-2]
    data[t] = {
        "close": round(latest['Close'], 2),
        "change": round((latest['Close']-prev['Close'])/prev['Close']*100, 2)
    }

# 比特幣
btc = yf.Ticker('BTC-USD').history(period='2d')
if len(btc) < 2:
    print("警告：BTC 沒有足夠的資料")
    data['BTC'] = {"close": None, "change": None}
else:
    data['BTC'] = {
        "close": round(btc.iloc[-1]['Close'], 2),
        "change": round((btc.iloc[-1]['Close']-btc.iloc[-2]['Close'])/btc.iloc[-2]['Close']*100, 2)
    }

# 黃金
gold = yf.Ticker('GC=F').history(period='2d')
if len(gold) < 2:
    print("警告：Gold 沒有足夠的資料")
    data['Gold'] = {"close": None, "change": None}
else:
    data['Gold'] = {
        "close": round(gold.iloc[-1]['Close'], 2),
        "change": round((gold.iloc[-1]['Close']-gold.iloc[-2]['Close'])/gold.iloc[-2]['Close']*100, 2)
    }

# 10年美債殖利率
treasury = yf.Ticker('^TNX').history(period='2d')
if len(treasury) < 2:
    print("警告：US10Y 沒有足夠的資料")
    data['US10Y'] = {"close": None, "change": None}
else:
    data['US10Y'] = {
        "close": round(treasury.iloc[-1]['Close'], 2),
        "change": round((treasury.iloc[-1]['Close']-treasury.iloc[-2]['Close'])/treasury.iloc[-2]['Close']*100, 2)
    }

# 熱門股範例，簡化處理
data['Top5'] = ['AAPL', 'TSLA', 'NVDA', 'AMZN', 'META']

with open('podcast/latest/market.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)