from datetime import datetime, timedelta
import os
from time import sleep
import pandas as pd
import pytz
import vectorbt as vbt
import twstock
import yfinance as yf

# 定義要處理的股票/ETF代碼
target_codes = {
    '2330': '台積電',
    '0050': '元大台灣50'
}

def clean_csv(csv_path):
    """清理CSV檔案，確保欄位數量一致"""
    expected_columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        if not lines:
            return

        with open(csv_path, 'w', encoding='utf-8') as file:
            header = lines[0].strip()
            if header.split(',') == expected_columns:
                file.write(header + '\n')
                for line in lines[1:]:
                    if len(line.split(',')) == len(expected_columns):
                        file.write(line)
    except Exception as e:
        print(f"[{csv_path}] 清理CSV檔案時發生錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] 清理CSV檔案 {csv_path} 錯誤: {e}\n")

def get_data_since_last_record(stock_num, stock_name, base_path='./data/'):
    """下載並追加自上次記錄以來的股票/ETF資料"""
    csv_path = f'{base_path}{stock_num}.csv'
    tz_taipei = pytz.timezone('Asia/Taipei')
    today = datetime.now(tz_taipei).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=59)

    # 驗證股票代碼
    try:
        ticker = yf.Ticker(f"{stock_num}.TW")
        if not ticker.history(period='1d').empty:
            print(f"[{stock_num}] 有效股票代碼: {stock_name}")
        else:
            print(f"[{stock_num}] 無效或已下市股票代碼: {stock_name}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {stock_num} 無效或已下市\n")
            return pd.DataFrame()
    except Exception as e:
        print(f"[{stock_num}] 股票代碼驗證錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {stock_num} 驗證錯誤: {e}\n")
        return pd.DataFrame()

    # 檢查現有資料
    if os.path.exists(csv_path):
        try:
            clean_csv(csv_path)
            data = pd.read_csv(csv_path, header=0)
            if not data.empty and 'Datetime' in data.columns:
                last_record = pd.to_datetime(data['Datetime'].iloc[-1], errors='coerce')
                if pd.notna(last_record):
                    if last_record.tzinfo is None:
                        last_record = last_record.tz_localize('Asia/Taipei', ambiguous='infer')
                    else:
                        last_record = last_record.tz_convert('Asia/Taipei')
                    start_date = last_record + timedelta(minutes=5)
        except Exception as e:
            print(f"[{stock_num}] CSV處理錯誤: {e}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {stock_num} CSV處理錯誤: {e}\n")

    end_date = today + timedelta(hours=14)

    try:
        yf_data = vbt.YFData.download(
            f"{stock_num}.TW",
            start=start_date.strftime('%Y-%m-%d %H:%M:%S%z'),
            end=end_date.strftime('%Y-%m-%d %H:%M:%S%z'),
            interval='5m',
            missing_index='drop'
        )
        new_data = yf_data.get()

        if new_data.empty:
            print(f"[{stock_num}] 無新資料下載: {stock_name}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {stock_num} 無新資料\n")
            return pd.DataFrame()

        # 避免重複資料
        if os.path.exists(csv_path):
            existing_data = pd.read_csv(csv_path)
            new_data = new_data[~new_data.index.isin(existing_data['Datetime'])]
            if not new_data.empty:
                new_data.to_csv(csv_path, mode='a', header=False, encoding='utf-8')
        else:
            new_data.to_csv(csv_path, encoding='utf-8')

        print(f"[{stock_num}] 資料已更新，共 {len(new_data)} 筆: {stock_name}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {stock_num} 更新 {len(new_data)} 筆資料\n")

        sleep(2)
        return new_data

    except Exception as e:
        print(f"[{stock_num}] 下載錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {stock_num} 下載錯誤: {e}\n")
        return pd.DataFrame()

def main():
    """主程式：僅處理2330和0050"""
    os.makedirs('./data/', exist_ok=True)

    with open('log.txt', 'a', encoding='utf-8') as log:
        log.write(f"[{datetime.now()}] 開始執行股票資料下載（2330, 0050）\n")

    for stock_num, stock_name in target_codes.items():
        print(f"正在處理: {stock_num} - {stock_name}")
        new_data = get_data_since_last_record(stock_num, stock_name)
        if new_data.empty:
            print(f"[{stock_num}] 無新資料或下載失敗: {stock_name}")
        else:
            print(f"[{stock_num}] 資料已更新，共 {len(new_data)} 筆: {stock_name}")

if __name__ == "__main__":
    main()