import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import logging
import asyncio
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
    """驗證數據品質，包括漲跌計算檢查"""
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
    return True

def validate_trend_consistency(df, benchmark_df, symbol):
    """驗證趨勢與大盤一致性"""
    if not benchmark_df.empty:
        df_change = df['Close'].pct_change().iloc[-1] * 100
        benchmark_change = benchmark_df['Close'].pct_change().iloc[-1] * 100
        if (df_change > 0) != (benchmark_change > 0) and abs(df_change) > 5:
            logger.warning(f"{symbol} 趨勢與大盤不一致: {df_change:.2f}% vs {benchmark_change:.2f}%")

async def fetch_and_save(symbol, interval, start_date, end_date, data_type):
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
            df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_convert('Asia/Taipei')
            df.rename(columns={'index': 'Date'}, inplace=True)
            for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            if validate_data(df, symbol):
                path = os.path.join('data', f'{data_type}_{symbol}.csv')
                df.to_csv(path, index=False, encoding='utf-8', float_format='%.2f')
                logger.info(f"成功抓取 {symbol} 的 {len(df)} 筆{data_type}數據，保存至 {path}")
                return df
            else:
                logger.error(f"{symbol} 數據驗證失敗，不保存")
                return None
        else:
            logger.warning(f"{symbol} 未返回{data_type}數據")
            return None
    except Exception as e:
        logger.error(f"抓取 {symbol} {data_type}數據失敗: {e}")
        return None

async def main():
    """主函數，執行資料收集"""
    symbols, data_sources, retain_daily, retain_hourly = load_config()
    end_date = datetime.now(tz)
    start_date_daily = end_date - timedelta(days=retain_daily + 1)
    start_date_hourly = end_date - timedelta(days=retain_hourly + 1)

    # 確保基準數據在循環前完成
    benchmark_symbol = '^TWII'
    benchmark_task = fetch_and_save(benchmark_symbol, '1d', start_date_daily, end_date, 'daily')
    benchmark_df = await benchmark_task if benchmark_task else pd.DataFrame()

    tasks = []
    for symbol in symbols:
        daily_task = fetch_and_save(symbol, '1d', start_date_daily, end_date, 'daily')
        hourly_task = fetch_and_save(symbol, '1h', start_date_hourly, end_date, 'hourly')
        tasks.extend([daily_task, hourly_task])
        # 只有當基準數據有效時才驗證趨勢
        if symbol != benchmark_symbol and not benchmark_df.empty:
            daily_df = await daily_task if daily_task else None
            if daily_df is not None:
                validate_trend_consistency(daily_df, benchmark_df, symbol)

    # 等待所有任務完成
    if tasks:
        await asyncio.gather(*tasks)

    clean_old_data()

if __name__ == '__main__':
    asyncio.run(main())