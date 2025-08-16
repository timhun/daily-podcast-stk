#fetch_market_data.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import logging
import time

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_data_directory():
    """移除 data/ 目錄中的無關檔案，保留預期輸出"""
    expected_files = {
        'daily.csv', 'daily_0050.TW.csv', 'daily_QQQ.csv',
        'hourly_0050.TW.csv', 'hourly_QQQ.csv',
        'daily_sim_0050.TW.json', 'daily_sim_QQQ.json',
        'backtest_report_0050.TW.json', 'backtest_report_QQQ.json',
        'strategy_history_0050.TW.json', 'strategy_history_QQQ.json',
        'podcast_script.txt'
    }
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    logger.info("檢查 data 目錄以進行清理...")
    removed_files = []
    for file in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file)
        if file not in expected_files and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                removed_files.append(file)
                logger.info(f"已移除無關檔案: {file}")
            except Exception as e:
                logger.warning(f"無法移除 {file}: {e}")
    if not removed_files:
        logger.info("無需清理，data 目錄中無無關檔案")
    else:
        logger.info("data 目錄清理完成")

def fetch_market_data():
    """抓取市場數據，支持 0050.TW 和 QQQ"""
    # 清理 data 目錄
    clean_data_directory()

    mode = os.getenv('PODCAST_MODE', 'tw')
    symbol = '0050.TW' if mode == 'tw' else 'QQQ'
    end_date = datetime.now()
    start_date_daily = end_date - timedelta(days=90)  # 過去3個月
    start_date_hourly = end_date - timedelta(days=7)   # 過去7天

    logger.info(f"開始抓取 {symbol} 日線數據")
    try:
        df_daily = yf.download(symbol, start=start_date_daily, end=end_date, interval='1d', auto_adjust=False, progress=False)
        if not df_daily.empty:
            df_daily['Symbol'] = symbol
            if 'Adj Close' not in df_daily.columns:
                logger.warning(f"{symbol} 無 'Adj Close' 欄位，使用 'Close'")
                df_daily['Adj Close'] = df_daily['Close']
            df_daily = df_daily[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].copy()
            df_daily.reset_index(inplace=True)  # 將日期從索引轉為欄位
            if 'Date' not in df_daily.columns:  # 確保 Date 欄位存在
                df_daily['Date'] = df_daily.index
                df_daily['Date'] = pd.to_datetime(df_daily['Date'])
            df_daily.rename(columns={'index': 'Date'}, inplace=True)  # 確保日期欄位名為 'Date'
            logger.info(f"成功抓取 {symbol} 的 {len(df_daily)} 筆日線數據，欄位: {df_daily.columns.tolist()}")
            # 保存單獨檔案
            daily_symbol_path = os.path.join('data', f'daily_{symbol}.csv')
            df_daily.to_csv(daily_symbol_path, index=False, encoding='utf-8')
            logger.info(f"已生成/覆蓋檔案: {daily_symbol_path}, 形狀: {df_daily.shape}")
            # 保存合併檔案（僅保留最新符號數據）
            daily_path = os.path.join('data', 'daily.csv')
            df_daily.to_csv(daily_path, index=False, encoding='utf-8')
            logger.info(f"已生成/覆蓋檔案: {daily_path}, 形狀: {df_daily.shape}")
            time.sleep(0.1)  # 確保時間戳更新
        else:
            logger.warning(f"{symbol} 未返回日線數據，可能是非交易日或數據不可用")
    except Exception as e:
        logger.error(f"抓取 {symbol} 日線數據失敗: {str(e)}")

    logger.info(f"開始抓取 {symbol} 小時線數據")
    try:
        df_hourly = yf.download(symbol, start=start_date_hourly, end=end_date, interval='1h', auto_adjust=False, progress=False)
        if not df_hourly.empty:
            df_hourly['Symbol'] = symbol
            if 'Adj Close' not in df_hourly.columns:
                logger.warning(f"{symbol} 無 'Adj Close' 欄位，使用 'Close'")
                df_hourly['Adj Close'] = df_hourly['Close']
            df_hourly = df_hourly[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].copy()
            df_hourly.reset_index(inplace=True)  # 將日期從索引轉為欄位
            if 'Date' not in df_hourly.columns:  # 確保 Date 欄位存在
                df_hourly['Date'] = df_hourly.index
                df_hourly['Date'] = pd.to_datetime(df_hourly['Date'])
            df_hourly.rename(columns={'index': 'Date'}, inplace=True)  # 確保日期欄位名為 'Date'
            hourly_symbol_path = os.path.join('data', f'hourly_{symbol}.csv')
            df_hourly.to_csv(hourly_symbol_path, index=False, encoding='utf-8')
            logger.info(f"已生成/覆蓋檔案: {hourly_symbol_path}, 形狀: {df_hourly.shape}")
            time.sleep(0.1)  # 確保時間戳更新
        else:
            logger.warning(f"{symbol} 未返回小時線數據，可能是非交易日或數據不可用")
    except Exception as e:
        logger.error(f"抓取 {symbol} 小時線數據失敗: {str(e)}")
    
    logger.info(f"{symbol} 市場數據抓取完成")
    # 驗證生成的檔案
    for filename in [daily_symbol_path, daily_path, hourly_symbol_path]:
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            logger.info(f"檔案 {filename} 大小: {file_size} bytes")
        else:
            logger.warning(f"檔案 {filename} 未生成")

if __name__ == '__main__':
    fetch_market_data()
