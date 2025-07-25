import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import requests

OUTPUT_PATH = "docs/podcast/bullish_signal_tw.txt"

def get_tw_stock_data_yf(symbol, days=90):
    ticker = yf.Ticker(f"{symbol}.TW")
    df = ticker.history(period=f"{days}d", interval="1d")
    if df.empty or len(df) < 60:
        return None
    return df

def get_backup_price_volume(symbol):
    try:
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=&stockNo={symbol}"
        resp = requests.get(url)
        data = resp.json()
        rows = data.get("data", [])
        prices = []
        volumes = []
        dates = []
        for row in rows:
            try:
                close = float(row[6].replace(",", ""))
                volume = int(row[1].replace(",", ""))
                date_str = row[0].replace("/", "-")
                dates.append(date_str)
                prices.append(close)
                volumes.append(volume)
            except:
                continue
        if len(prices) < 60:
            return None
        series_price = pd.Series(prices[-60:], index=pd.to_datetime(dates[-60:]))
        series_volume = pd.Series(volumes[-60:], index=pd.to_datetime(dates[-60:]))
        return pd.DataFrame({"Close": series_price, "Volume": series_volume})
    except:
        return None

def fallback_stock_data(symbol):
    df = get_tw_stock_data_yf(symbol)
    if df is not None:
        return df

    df = get_backup_price_volume(symbol)
    if df is not None:
        return df

    raise RuntimeError(f"❌ 無法取得 {symbol} 的股價資料")

def calculate_signals(df):
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    df["Bullish"] = (df["MA5"] > df["MA10"]) & (df["MA10"] > df["MA60"])

    weights = [0.4, 0.35, 0.25]
    df["BigLine"] = (
        weights[0] * df["MA5"] +
        weights[1] * df["MA10"] +
        weights[2] * df["MA60"]
    )

    vol_max = df["Volume"].rolling(60).max()
    df["VolFactor"] = 1 + df["Volume"] / (vol_max + 1e-9)
    df["BigLine_Weighted"] = df["BigLine"] * df["VolFactor"]
    df["BigLine_Change"] = df["BigLine_Weighted"].diff()

    return df

def interpret_result(name, df: pd.DataFrame) -> str:
    latest = df.dropna().iloc[-1]
    trend = "多頭排列 ✅" if latest["Bullish"] else "尚未成形 ⚠️"
    direction = "↗️ 上升" if latest["BigLine_Change"] > 0 else "↘️ 下降"
    return f"{name}：{trend}，大盤線方向：{direction}"

def main():
    print("🔍 擷取台股資料進行多空判斷...")

    try:
        df_twii = fallback_stock_data("^TWII")
        df_0050 = fallback_stock_data("0050")
    except Exception as e:
        print(f"❌ 資料抓取錯誤：{e}")
        return

    df_twii = calculate_signals(df_twii)
    df_0050 = calculate_signals(df_0050)

    result_twii = interpret_result("加權指數", df_twii)
    result_0050 = interpret_result("0050", df_0050)

    result_text = f"📈 台股市場多空判斷（{datetime.now().strftime('%Y年%m月%d日')}）\n\n{result_twii}\n{result_0050}\n"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(result_text)

    print("✅ 已產出台股多空判斷：", OUTPUT_PATH)
    print(result_text)

if __name__ == "__main__":
    main()