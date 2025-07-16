import yfinance as yf
import json

def fetch_data():
    symbols = ['^DJI', '^IXIC', '^GSPC', '^SOX', 'QQQ']
    result = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else close
            pct_change = ((close - prev_close) / prev_close) * 100
            result[symbol] = {"close": round(close, 2), "pct": round(pct_change, 2)}
    with open("data.json", "w") as f:
        json.dump(result, f)

if __name__ == "__main__":
    fetch_data()
