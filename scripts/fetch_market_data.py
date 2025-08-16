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
    """Remove irrelevant files from data/ directory, keeping expected outputs."""
    expected_files = {
        'daily.csv', 'hourly_0050.csv', 'hourly_TWII.csv', 'hourly_2330.csv',
        'daily_sim.json', 'backtest_report.json', 'strategy_history.json', 'podcast_script.txt'
    }
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    for file in glob.glob(f"{data_dir}/*"):
        if os.path.basename(file) not in expected_files:
            try:
                os.remove(file)
                logger.info(f"Removed irrelevant file: {file}")
            except Exception as e:
                logger.warning(f"Failed to remove {file}: {e}")

def fetch_market_data():
    # 清理 data/ 目錄
    clean_data_directory()

    # 定義標的
    symbols = ['^TWII', '0050.TW', '2330.TW']
    end_date = datetime.now()
    start_date_daily = end_date - timedelta(days=90)  # 過去3個月
    start_date_hourly = end_date - timedelta(days=7)   # 過去7天

    # 抓取日線數據
    daily_data = []
    for symbol in symbols:
        logger.info(f"Fetching daily data for {symbol}")
        try:
            df = yf.download(symbol, start=start_date_daily, end=end_date, interval='1d', auto_adjust=False, progress=False)
            if not df.empty:
                df['Symbol'] = symbol
                # 檢查是否有 'Adj Close'，若無則用 'Close' 填充
                if 'Adj Close' not in df.columns:
                    logger.warning(f"No 'Adj Close' column for {symbol}, using 'Close'")
                    df['Adj Close'] = df['Close']
                daily_data.append(df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']])
                logger.info(f"Successfully fetched {len(df)} daily rows for {symbol}")
            else:
                logger.warning(f"No daily data returned for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching daily data for {symbol}: {e}")
    
    if daily_data:
        daily_df = pd.concat(daily_data)
        daily_df.to_csv('data/daily.csv', index=True, encoding='utf-8')
        logger.info(f"daily.csv saved with shape: {daily_df.shape}")
    else:
        logger.error("No daily data to save for any symbol")

    # 抓取小時線數據並儲存到個別檔案
    for symbol in symbols:
        logger.info(f"Fetching hourly data for {symbol}")
        try:
            df = yf.download(symbol, start=start_date_hourly, end=end_date, interval='1h', auto_adjust=False, progress=False)
            if not df.empty:
                df['Symbol'] = symbol
                # 檢查是否有 'Adj Close'，若無則用 'Close' 填充
                if 'Adj Close' not in df.columns:
                    logger.warning(f"No 'Adj Close' column for {symbol}, using 'Close'")
                    df['Adj Close'] = df['Close']
                # 保存到個別檔案
                filename = f"hourly_{symbol.replace('^', '').replace('.TW', '')}.csv"
                df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].to_csv(
                    f'data/{filename}', index=True, encoding='utf-8'
                )
                logger.info(f"{filename} saved with shape: {df.shape}")
            else:
                logger.warning(f"No hourly data returned for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching hourly data for {symbol}: {e}")

if __name__ == '__main__':
    fetch_market_data()