from datetime import datetime, timedelta
import os
from time import sleep
import pandas as pd
import pytz
import urllib.request
import re
import yfinance as yf
import argparse

# 定義要處理的市場指數及個股（可擴充）
target_symbols = [
    {'name': 'S&P 500', 'yahoo_symbol': '^GSPC', 'google_code': '.INX:INDEXSP'},
    {'name': 'Dow Jones', 'yahoo_symbol': '^DJI', 'google_code': '.DJI:INDEXDJX'},
    {'name': 'Nasdaq', 'yahoo_symbol': '^IXIC', 'google_code': '.IXIC:INDEXNASDAQ'},
    {'name': 'TAIEX', 'yahoo_symbol': '^TWII', 'google_code': 'IX0001:TPE'},
    {'name': '台積電', 'yahoo_symbol': '2330.TW', 'google_code': '2330:TPE'},
    {'name': '元大台灣50', 'yahoo_symbol': '0050.TW', 'google_code': '0050:TPE'},
    # 可擴充示例：添加美股或台股
    # {'name': 'Apple', 'yahoo_symbol': 'AAPL', 'google_code': 'AAPL:NASDAQ'},
    # {'name': '台達電', 'yahoo_symbol': '2308.TW', 'google_code': '2308:TPE'},
]

def validate_stock_code(yahoo_symbol):
    """驗證股票/指數代碼是否有效"""
    try:
        ticker = yf.Ticker(yahoo_symbol)
        history = ticker.history(period='1d')
        return not history.empty
    except Exception as e:
        print(f"[{yahoo_symbol}] 股票/指數代碼驗證錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {yahoo_symbol} 驗證錯誤: {e}\n")
        return False

def clean_csv(csv_path):
    """清理CSV檔案，確保欄位數量一致"""
    expected_columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
    try:
        # 檢查檔案是否為空
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            print(f"[{csv_path}] 檔案不存在或為空，初始化新檔案")
            pd.DataFrame(columns=expected_columns).to_csv(csv_path, index=False, encoding='utf-8')
            return

        with open(csv_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        if not lines:
            print(f"[{csv_path}] 檔案無內容，初始化新檔案")
            pd.DataFrame(columns=expected_columns).to_csv(csv_path, index=False, encoding='utf-8')
            return

        # 檢查欄位
        header = lines[0].strip().split(',')
        if header != expected_columns:
            print(f"[{csv_path}] 欄位不符，初始化新檔案")
            pd.DataFrame(columns=expected_columns).to_csv(csv_path, index=False, encoding='utf-8')
            return

        # 清理無效行
        with open(csv_path, 'w', encoding='utf-8') as file:
            file.write(','.join(expected_columns) + '\n')
            for line in lines[1:]:
                if len(line.split(',')) == len(expected_columns):
                    file.write(line)
    except Exception as e:
        print(f"[{csv_path}] 清理CSV檔案時發生錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] 清理CSV檔案 {csv_path} 錯誤: {e}\n")
        # 初始化新檔案以避免後續錯誤
        pd.DataFrame(columns=expected_columns).to_csv(csv_path, index=False, encoding='utf-8')

def get_google_finance_data(google_code, stock_name):
    """從 Google Finance 抓取當日即時股價"""
    url = f"https://www.google.com/finance/quote/{google_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"[{google_code}] Google Finance 頁面下載錯誤: {e}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {google_code} Google Finance 頁面下載錯誤: {e}\n")
        return None

    # 提取當前價格
    current_price = re.search(r'<div class="YMlKec fxKbKc">([\d,]+\.?\d*)</div>', html)
    if not current_price:
        print(f"[{google_code}] 無法提取當前價格: {stock_name}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {google_code} 無法提取當前價格\n")
        return None

    tz_taipei = pytz.timezone('Asia/Taipei')
    current_time = datetime.now(tz_taipei)
    
    # 以 Yahoo Finance 格式構造資料
    data_dict = {
        'Datetime': current_time,  # 直接使用 Timestamp 物件
        'Open': 'NA',
        'High': 'NA',
        'Low': 'NA',
        'Close': float(current_price.group(1).replace(',', '')),
        'Volume': 'NA'
    }
    return pd.DataFrame([data_dict])

def get_yahoo_finance_data(yahoo_symbol, stock_name, data_dir='data', max_retries=3):
    """從 Yahoo Finance 抓取90天歷史1小時K線資料"""
    csv_filename = yahoo_symbol.replace('^', '').replace('.', '_') + '.csv'
    csv_path = os.path.join(data_dir, csv_filename)
    tz_taipei = pytz.timezone('Asia/Taipei')
    today = datetime.now(tz_taipei).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=90)

    # 驗證股票代碼
    if not validate_stock_code(yahoo_symbol):
        print(f"[{yahoo_symbol}] 無效或已下市股票代碼: {stock_name}")
        with open('log.txt', 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {yahoo_symbol} 無效或已下市\n")
        return pd.DataFrame()

    # 檢查現有資料
    if os.path.exists(csv_path):
        try:
            clean_csv(csv_path)
            existing_data = pd.read_csv(csv_path, header=0, parse_dates=['Datetime'])
            if not existing_data.empty and 'Datetime' in existing_data.columns:
                last_record = pd.to_datetime(existing_data['Datetime'].iloc[-1], errors='coerce')
                if pd.notna(last_record):
                    if last_record.tzinfo is None:
                        last_record = last_record.tz_localize('Asia/Taipei', ambiguous='infer')
                    else:
                        last_record = last_record.tz_convert('Asia/Taipei')
                    start_date = last_record + timedelta(hours=1)  # 匹配1小時K線
        except Exception as e:
            print(f"[{yahoo_symbol}] CSV處理錯誤: {e}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} CSV處理錯誤: {e}\n")
            # 初始化新檔案
            pd.DataFrame(columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']).to_csv(csv_path, index=False, encoding='utf-8')

    end_date = today + timedelta(hours=14)

    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(yahoo_symbol)
            new_data = ticker.history(
                start=start_date,
                end=end_date,
                interval='1h',
                auto_adjust=True,
                prepost=False
            )

            if new_data.empty:
                print(f"[{yahoo_symbol}] 無新歷史資料下載: {stock_name}")
                with open('log.txt', 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] {yahoo_symbol} 無新歷史資料\n")
                return pd.DataFrame()

            new_data = new_data.reset_index()
            new_data = new_data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
            new_data['Datetime'] = new_data['Datetime'].dt.tz_convert('Asia/Taipei')

            return new_data

        except Exception as e:
            print(f"[{yahoo_symbol}] Yahoo Finance 抓取失敗（嘗試 {attempt + 1}/{max_retries}）：{e}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} Yahoo Finance 抓取失敗（嘗試 {attempt + 1}/{max_retries}）：{e}\n")
            if attempt < max_retries - 1:
                sleep(2 ** attempt)
            continue
        else:
            print(f"[{yahoo_symbol}] Yahoo Finance 抓取失敗，跳過")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} Yahoo Finance 抓取失敗，跳過\n")
            return pd.DataFrame()

def fetch_and_update_data(symbols, data_dir='data', max_retries=3):
    """抓取並更新市場指數及個股資料"""
    os.makedirs(data_dir, exist_ok=True)

    with open('log.txt', 'a', encoding='utf-8') as log:
        log.write(f"[{datetime.now()}] 開始執行資料抓取\n")

    for symbol in symbols:
        yahoo_symbol = symbol['yahoo_symbol']
        google_code = symbol['google_code']
        stock_name = symbol['name']
        print(f"正在處理: {yahoo_symbol} - {stock_name}")

        csv_filename = yahoo_symbol.replace('^', '').replace('.', '_') + '.csv'
        csv_path = os.path.join(data_dir, csv_filename)

        # 抓取 Yahoo Finance 歷史資料
        yahoo_data = get_yahoo_finance_data(yahoo_symbol, stock_name, data_dir, max_retries)
        
        # 抓取 Google Finance 即時資料
        google_data = get_google_finance_data(google_code, stock_name)

        # 合併資料
        if not yahoo_data.empty and google_data is not None:
            combined_data = pd.concat([yahoo_data, google_data], ignore_index=True)
        elif not yahoo_data.empty:
            combined_data = yahoo_data
        elif google_data is not None:
            combined_data = google_data
        else:
            print(f"[{yahoo_symbol}] 無任何資料可整合: {stock_name}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} 無任何資料可整合\n")
            continue

        # 確保 Datetime 欄位為 Timestamp
        combined_data['Datetime'] = pd.to_datetime(combined_data['Datetime'], errors='coerce')
        combined_data = combined_data.dropna(subset=['Datetime'])  # 移除無效 Datetime

        # 清理舊資料（僅保留90天）
        if os.path.exists(csv_path):
            try:
                existing_data = pd.read_csv(csv_path, parse_dates=['Datetime'])
                existing_data['Datetime'] = pd.to_datetime(existing_data['Datetime'], errors='coerce')
                existing_data = existing_data.dropna(subset=['Datetime'])
                combined_data = pd.concat([existing_data, combined_data], ignore_index=True)
                tz_taipei = pytz.timezone('Asia/Taipei')
                cutoff = datetime.now(tz_taipei) - timedelta(days=90)
                combined_data = combined_data[combined_data['Datetime'] >= cutoff]
            except Exception as e:
                print(f"[{yahoo_symbol}] 合併現有資料錯誤: {e}")
                with open('log.txt', 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] {yahoo_symbol} 合併現有資料錯誤: {e}\n")
                # 初始化新檔案
                combined_data = combined_data[combined_data['Datetime'] >= cutoff]

        # 移除重複的 Datetime
        combined_data = combined_data.sort_values('Datetime').drop_duplicates(subset=['Datetime'], keep='last')

        # 儲存到 CSV
        if not combined_data.empty:
            combined_data.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"[{yahoo_symbol}] 資料已更新，共 {len(combined_data)} 筆: {stock_name}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} 更新 {len(combined_data)} 筆資料\n")
        else:
            print(f"[{yahoo_symbol}] 無新資料儲存: {stock_name}")
            with open('log.txt', 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] {yahoo_symbol} 無新資料儲存\n")

        sleep(2)  # 避免觸發速率限制

    print('資料抓取與更新完成！')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and update market data")
    parser.add_argument('--tickers', type=str, help="Comma-separated list of Yahoo tickers (e.g., ^GSPC,^DJI,2330.TW)")
    args = parser.parse_args()

    if args.tickers:
        tickers = args.tickers.split(',')
        # 為命令列輸入的 ticker 生成 symbols 格式
        symbols = [{'name': ticker, 'yahoo_symbol': ticker, 'google_code': ticker.replace('.TW', ':TPE').replace('^', '.').replace('GSPC', 'INX:INDEXSP').replace('DJI', 'DJI:INDEXDJX').replace('IXIC', 'IXIC:INDEXNASDAQ').replace('TWII', 'IX0001:TPE')} for ticker in tickers]
    else:
        symbols = target_symbols

    fetch_and_update_data(symbols)