import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import logging
import glob

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_data_directory():
    """移除 data/ 目錄中的無關檔案，保留預期輸出"""
    expected_files = {
        'daily.csv', 'daily_0050.csv', 'daily_TWII.csv', 'daily_2330.csv',
        'hourly_0050.csv', 'hourly_TWII.csv', 'hourly_2330.csv',
        'daily_sim.json', 'backtest_report.json', 'strategy_history.json', 'podcast_script.txt'
    }
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    logger.info("檢查 data 目錄以進行清理...")
    for file in glob.glob(f"{data_dir}/*"):
        if os.path.basename(file) not in expected_files:
            try:
                os.remove(file)
                logger.info(f"已移除無關檔案: {file}")
            except Exception as e:
                logger.warning(f"無法移除 {file}: {e}")
    logger.info("data 目錄清理完成")

def fetch_market_data(split_daily=True):
    """抓取市場數據，split_daily=True 時生成單獨的日線檔案"""
    # 清理 data 目錄
    clean_data_directory()

    # 定義標的
    symbols = ['^TWII', '0050.TW', '2330.TW']
    end_date = datetime.now()
    start_date_daily = end_date - timedelta(days=90)  # 過去3個月
    start_date_hourly = end_date - timedelta(days=7)   # 過去7天

    logger.info("開始抓取所有標的日線數據")
    # 抓取日線數據
    daily_data = []
    for symbol in symbols:
        logger.info(f"抓取 {symbol} 的日線數據")
        try:
            df = yf.download(symbol, start=start_date_daily, end=end_date, interval='1d', auto_adjust=False, progress=False)
            if not df.empty:
                df['Symbol'] = symbol
                # 檢查是否有 'Adj Close'，若無則用 'Close' 填充
                if 'Adj Close' not in df.columns:
                    logger.warning(f"{symbol} 無 'Adj Close' 欄位，使用 'Close'")
                    df['Adj Close'] = df['Close']
                df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].copy()
                daily_data.append(df)
                logger.info(f"成功抓取 {symbol} 的 {len(df)} 筆日線數據")
                # 保存單獨檔案
                if split_daily:
                    filename = f"daily_{symbol.replace('^', '').replace('.TW', '')}.csv"
                    df.to_csv(f'data/{filename}', index=True, encoding='utf-8')
                    logger.info(f"{filename} 已保存，形狀: {df.shape}")
            else:
                logger.warning(f"{symbol} 未返回日線數據")
        except Exception as e:
            logger.error(f"抓取 {symbol} 日線數據失敗: {e}")
    
    if daily_data:
        daily_df = pd.concat(daily_data)
        daily_df.to_csv('data/daily.csv', index=True, encoding='utf-8')
        logger.info(f"daily.csv 已保存，形狀: {daily_df.shape}")
    else:
        logger.error("無任何標的日線數據可保存")

    logger.info("開始抓取所有標的小時線數據")
    # 抓取小時線數據並儲存到個別檔案
    for symbol in symbols:
        logger.info(f"抓取 {symbol} 的小時線數據")
        try:
            df = yf.download(symbol, start=start_date_hourly, end=end_date, interval='1h', auto_adjust=False, progress=False)
            if not df.empty:
                df['Symbol'] = symbol
                # 檢查是否有 'Adj Close'，若無則用 'Close' 填充
                if 'Adj Close' not in df.columns:
                    logger.warning(f"{symbol} 無 'Adj Close' 欄位，使用 'Close'")
                    df['Adj Close'] = df['Close']
                df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].copy()
                # 保存到個別檔案
                filename = f"hourly_{symbol.replace('^', '').replace('.TW', '')}.csv"
                df.to_csv(f'data/{filename}', index=True, encoding='utf-8')
                logger.info(f"{filename} 已保存，形狀: {df.shape}")
            else:
                logger.warning(f"{symbol} 未返回小時線數據")
        except Exception as e:
            logger.error(f"抓取 {symbol} 小時線數據失敗: {e}")
    
    logger.info("市場數據抓取完成")

if __name__ == '__main__':
    fetch_market_data(split_daily=True)
