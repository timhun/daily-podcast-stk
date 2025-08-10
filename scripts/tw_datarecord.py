import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# 定義股票/指數代碼和輸出資料夾
tickers = ['^TWII', '0050.TW', 'QQQ']
data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)  # 確保 data 資料夾存在

# 定義抓取三個月資料的時間範圍
end_date = datetime.today()
start_date = end_date - timedelta(days=90)  # 三個月前

# 處理每個 ticker
for ticker in tickers:
    # 定義 CSV 檔案路徑
    csv_file = os.path.join(data_dir, f'{ticker.replace("^", "")}.csv')
    
    # 嘗試讀取現有 CSV 檔案
    existing_data = None
    if os.path.exists(csv_file):
        existing_data = pd.read_csv(csv_file, parse_dates=['Date'])
        existing_data['Date'] = pd.to_datetime(existing_data['Date'])
    
    # 抓取最新歷史資料
    stock = yf.Ticker(ticker)
    new_data = stock.history(start=start_date, end=end_date)
    
    # 重置索引並確保 Date 欄位格式
    new_data = new_data.reset_index()
    new_data['Date'] = pd.to_datetime(new_data['Date'].dt.date)
    
    # 如果有現有資料，檢查是否有新資料
    if existing_data is not None:
        # 找出新資料中不在現有資料中的日期
        new_dates = new_data[~new_data['Date'].isin(existing_data['Date'])]
        if not new_dates.empty:
            # 合併新舊資料並排序
            combined_data = pd.concat([existing_data, new_dates], ignore_index=True)
            combined_data = combined_data.sort_values('Date').reset_index(drop=True)
            # 保存更新後的資料
            combined_data.to_csv(csv_file, index=False)
            print(f'已更新 {ticker} 的資料，新增 {len(new_dates)} 筆記錄')
        else:
            print(f'{ticker} 無新資料，跳過更新')
    else:
        # 如果沒有現有 CSV，直接保存新資料
        new_data.to_csv(csv_file, index=False)
        print(f'已為 {ticker} 創建新 CSV 檔案')

print('資料抓取與更新完成！')