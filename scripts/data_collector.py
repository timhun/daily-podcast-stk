import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import logging
from pytz import timezone

# 設定日誌，確保台灣時區
tz = timezone('Asia/Taipei')
logging.basicConfig(
    filename='logs/data_collector.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S CST'
)
logger = logging.getLogger(__name__)

def load_config():
    """載入 config.json 配置文件"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', []), config.get('data_sources', {'yfinance': {'enabled': True}}), config.get('retain_daily', 300), config.get('retain_hourly', 14)
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def clean_old_data(data_dir='data', retain_daily=300, retain_hourly=14):
    """清理舊數據，保留指定天數"""
    now = datetime.now(tz)
    for file in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file)
        if os.path.exists(file_path):
            if file.startswith('daily_') and file.endswith('.csv'):
                df = pd.read_csv(file_path)
                df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_convert('Asia/Taipei')
                df = df[df['Date'] >= now - timedelta(days=retain_daily)]
                df.to_csv(file_path, index=False, encoding='utf-8', float_format='%.2f')
                logger.info(f"清理 {file}，保留最近 {retain_daily} 天數據")
            elif file.startswith('hourly_') and file.endswith('.csv'):
                df = pd.read_csv(file_path)
                df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_convert('Asia/Taipei')
                df = df[df['Date'] >= now - timedelta(days=retain_hourly)]
                df.to_csv(file_path, index=False, encoding='utf-8', float_format='%.2f')
                logger.info(f"清理 {file}，保留最近 {retain_hourly} 天數據")

def validate_data(df, symbol):
    """驗證數據品質，包括漲跌異常檢查"""
    if df.empty:
        logger.warning(f"{symbol} 數據為空")
        return False
    if len(df) < 2:
        logger.warning(f"{symbol} 數據不足,無法計算漲跌")
        return False
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    df['Pct_Change'] = df['Close'].pct_change() * 100
    abnormal = df[(df['Pct_Change'] > 20) | (df['Pct_Change'] < -20)]
    if not abnormal.empty:
        logger.warning(f"{symbol} 漲跌異常: {abnormal[['Date', 'Pct_Change']].to_dict('records')}")
    return True

def fetch_and_save(symbol, interval, start_date, end_date, data_type, max_retries=3):
    """抓取並保存數據，支援錯誤重試"""
    for attempt in range(max_retries):
        try:
            df = yf.download(symbol, start=start_date, end=end_date, interval=interval, auto_adjust=False, progress=False)
            if not df.empty:
                df['Symbol'] = symbol
                if 'Adj Close' not in df.columns:
                    df['Adj Close'] = df['Close']
                df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Symbol']].copy()
                df.reset_index(inplace=True)
                if 'Date' not in df.columns:
                    df['Date'] = df.index
                df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_convert('Asia/Taipei')
                df.rename(columns={'index': 'Date'}, inplace=True)
                for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                if validate_data(df, symbol):
                    path = os.path.join('data', f'{data_type}_{symbol}.csv')
                    df.to_csv(path, index=False, encoding='utf-8', float_format='%.2f')
                    logger.info(f"成功抓取 {symbol} 的 {len(df)} 筆{data_type}數據，保存至 {path}")
                    return
            else:
                logger.warning(f"{symbol} 未返回{data_type}數據")
                return
        except Exception as e:
            logger.error(f"嘗試 {attempt + 1}/{max_retries} 抓取 {symbol} {data_type}數據失敗: {e}")
            if attempt < max_retries - 1:
                continue
            logger.error(f"{symbol} {data_type}數據抓取失敗，超過重試次數")

def main():
    """主函數，執行資料收集"""
    symbols, data_sources, retain_daily, retain_hourly = load_config()
    end_date = datetime.now(tz)
    start_date_daily = end_date - timedelta(days=retain_daily + 1)
    start_date_hourly = end_date - timedelta(days=retain_hourly + 1)

    for symbol in symbols:
        fetch_and_save(symbol, '1d', start_date_daily, end_date, 'daily')
        fetch_and_save(symbol, '1h', start_date_hourly, end_date, 'hourly')

    clean_old_data()

if __name__ == '__main__':
    main()