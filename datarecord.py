# datarecord.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def fetch_and_update_data(tickers, data_dir='data'):
    os.makedirs(data_dir, exist_ok=True)
    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)

    for ticker in tickers:
        csv_file = os.path.join(data_dir, f'{ticker.replace("^", "")}.csv')
        existing_data = None
        if os.path.exists(csv_file):
            existing_data = pd.read_csv(csv_file, parse_dates=['Date'])
            existing_data['Date'] = pd.to_datetime(existing_data['Date'])
        
        try:
            stock = yf.Ticker(ticker)
            new_data = stock.history(start=start_date, end=end_date)
            new_data = new_data.reset_index()
            new_data['Date'] = pd.to_datetime(new_data['Date'].dt.date)
            
            if existing_data is not None:
                new_dates = new_data[~new_data['Date'].isin(existing_data['Date'])]
                if not new_dates.empty:
                    combined_data = pd.concat([existing_data, new_dates], ignore_index=True)
                    combined_data = combined_data.sort_values('Date').reset_index(drop=True)
                    combined_data.to_csv(csv_file, index=False)
                    print(f'更新 {ticker} 資料，新增 {len(new_dates)} 筆')
                else:
                    print(f'{ticker} 無新資料')
            else:
                new_data.to_csv(csv_file, index=False)
                print(f'為 {ticker} 創建新 CSV')
        except Exception as e:
            print(f'抓取 {ticker} 資料失敗：{e}')
