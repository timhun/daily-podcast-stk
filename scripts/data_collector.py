import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import logging
import asyncio

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """載入配置檔案 config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', []), config.get('data_sources', {'default': 'yahoo'})
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

async def fetch_and_save(symbol, interval, start_date, end_date, data_type, benchmark_df=None):
    """異步抓取並保存數據"""
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
                df['Date'] = pd.to_datetime(df['Date'])
            df.rename(columns={'index': 'Date'}, inplace=True)
            for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            if await validate_data(df, symbol, benchmark_df):
                path = os.path.join('data', f'{data_type}_{symbol}.csv')
                df.to_csv(path, index=False, encoding='utf-8', float_format='%.2f')
                logger.info(f"成功抓取 {symbol} 的 {len(df)} 筆{data_type}數據，保存至 {path}")
                return True
            else:
                logger.error(f"{symbol} 數據驗證失敗，不保存")
                return False
        else:
            logger.warning(f"{symbol} 未返回{data_type}數據")
            return False
    except Exception as e:
        logger.error(f"抓取 {symbol} {data_type}數據失敗: {e}")
        return False

async def validate_data(df, symbol, benchmark_df):
    """驗證數據品質，包括漲跌計算和趨勢一致性檢查"""
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
    continuous_same = df['Close'].eq(df['Close'].shift()).sum() > len(df) * 0.1
    if continuous_same:
        logger.warning(f"{symbol} 連續數據一致性問題，可能有重複")
    if benchmark_df is not None and not benchmark_df.empty:
        df_change = df['Close'].pct_change().iloc[-1]
        benchmark_change = benchmark_df['Close'].pct_change().iloc[-1]
        if (df_change > 0) != (benchmark_change > 0) and abs(df_change) > 5:
            logger.warning(f"{symbol} 趨勢與大盤不一致: {df_change:.2f}% vs {benchmark_change:.2f}%")
    return True

def clean_old_data(data_dir='data', retain_daily=300, retain_hourly=14):
    """清理舊數據，保留指定天數"""
    now = datetime.now()
    for file in os.listdir(data_dir):
        if file.startswith('daily_') and file.endswith('.csv'):
            df = pd.read_csv(os.path.join(data_dir, file))
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[df['Date'] >= now - timedelta(days=retain_daily)]
            df.to_csv(os.path.join(data_dir, file), index=False, encoding='utf-8', float_format='%.2f')
            logger.info(f"清理 {file}，保留最近 {retain_daily} 天數據")
        elif file.startswith('hourly_') and file.endswith('.csv'):
            df = pd.read_csv(os.path.join(data_dir, file))
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[df['Date'] >= now - timedelta(days=retain_hourly)]
            df.to_csv(os.path.join(data_dir, file), index=False, encoding='utf-8', float_format='%.2f')
            logger.info(f"清理 {file}，保留最近 {retain_hourly} 天數據")

async def main():
    """主函數，執行資料收集"""
    symbols, data_sources = load_config()
    end_date = datetime.now()
    start_date_daily = end_date - timedelta(days=300 + 1)
    start_date_hourly = end_date - timedelta(days=14 + 1)
    benchmark_df = yf.download('^TWII', start=start_date_daily, end=end_date, interval='1d', progress=False)

    tasks = []
    for symbol in symbols:
        tasks.append(fetch_and_save(symbol, '1d', start_date_daily, end_date, 'daily', benchmark_df))
        tasks.append(fetch_and_save(symbol, '1h', start_date_hourly, end_date, 'hourly', benchmark_df))
    await asyncio.gather(*tasks)

    clean_old_data()

if __name__ == '__main__':
    asyncio.run(main())
