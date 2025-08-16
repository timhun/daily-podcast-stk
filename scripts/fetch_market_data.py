import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def fetch_market_data():
    # 定義標的
    symbols = ['^TWII', '0050.TW', '2330.TW']
    end_date = datetime.now()
    start_date_daily = end_date - timedelta(days=90)  # 過去3個月
    start_date_hourly = end_date - timedelta(days=7)   # 過去7天

    # 創建儲存目錄
    os.makedirs('data', exist_ok=True)

    # 抓取日線數據
    daily_data = []
    for symbol in symbols:
        df = yf.download(symbol, start=start_date_daily, end=end_date, interval='1d')
        if not df.empty:
            df['Symbol'] = symbol
            daily_data.append(df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']])
    daily_df = pd.concat(daily_data)
    daily_df.to_csv('data/daily.csv', index=True, encoding='utf-8')
    print(f"daily.csv saved with shape: {daily_df.shape}")

    # 抓取小時線數據
    hourly_data = []
    for symbol in symbols:
        df = yf.download(symbol, start=start_date_hourly, end=end_date, interval='1h')
        if not df.empty:
            df['Symbol'] = symbol
            hourly_data.append(df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']])
    hourly_df = pd.concat(hourly_data)
    hourly_df.to_csv('data/hourly.csv', index=True, encoding='utf-8')
    print(f"hourly.csv saved with shape: {hourly_df.shape}")

if __name__ == '__main__':
    fetch_market_data()