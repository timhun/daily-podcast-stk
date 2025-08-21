import yfinance as yf
import pandas as pd

def fetch_data(symbol="QQQ", start="2020-01-01"):
    df = yf.download(symbol, start=start)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df

if __name__ == "__main__":
    df = fetch_data()
    print(df.tail())
