import pandas as pd

def add_features(df: pd.DataFrame):
    df["SMA_10"] = df["Close"].rolling(10).mean()
    df["RSI"] = 100 - (100 / (1 + df["Close"].pct_change().rolling(14).mean()))
    df["Return"] = df["Close"].pct_change()
    df["Target"] = (df["Return"].shift(-1) > 0).astype(int)  # 明日漲跌
    df.dropna(inplace=True)
    return df

if __name__ == "__main__":
    import data
    df = data.fetch_data()
    df = add_features(df)
    print(df.tail())
