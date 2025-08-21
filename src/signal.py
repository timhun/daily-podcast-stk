import joblib
import pandas as pd
import json
import data, features

def generate_signal():
    df = data.fetch_data()
    df = features.add_features(df)

    model = joblib.load("model.pkl")
    latest = df.iloc[-1][["SMA_10", "RSI", "Return"]].fillna(0).values.reshape(1, -1)

    pred = model.predict(latest)[0]
    signal = "BUY" if pred == 1 else "SELL"

    output = {
        "date": str(df.index[-1].date()),
        "signal": signal,
        "close": float(df["Close"].iloc[-1])
    }

    with open("signal.json", "w") as f:
        json.dump(output, f, indent=2)

    return output

if __name__ == "__main__":
    print(generate_signal())
