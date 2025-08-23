# scripts/data_collector.py
import yfinance as yf
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
import logging
import pytz

logging.basicConfig(filename='logs/data_collector.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    tw_tz = pytz.timezone('Asia/Taipei')
    today = datetime.now(tw_tz)
    
    os.makedirs('data', exist_ok=True)
    
    all_symbols = config['symbols']['tw'] + config['symbols']['us']
    
    for symbol in all_symbols:
        for attempt in range(config['retry_times'] + 1):
            try:
                # Daily data (last 300 days)
                daily_data = yf.download(symbol, period=f"{config['data_retention_days']}d", interval="1d")
                if daily_data.empty:
                    raise ValueError("Empty data")
                daily_file = f"data/daily_{symbol.replace('.', '_').replace('^', '')}.csv"
                daily_data.to_csv(daily_file)
                logging.info(f"Downloaded daily data for {symbol}: {daily_data.shape}")
                
                # Hourly data (last 14 days)
                hourly_data = yf.download(symbol, period=f"{config['hourly_retention_days']}d", interval="1h")
                if hourly_data.empty:
                    raise ValueError("Empty data")
                hourly_file = f"data/hourly_{symbol.replace('.', '_').replace('^', '')}.csv"
                hourly_data.to_csv(hourly_file)
                logging.info(f"Downloaded hourly data for {symbol}: {hourly_data.shape}")
                
                time.sleep(config['delay_sec'])
                break
            except Exception as e:
                logging.error(f"Error for {symbol} (attempt {attempt}): {e}")
                if attempt == config['retry_times']:
                    raise
                time.sleep(config['delay_sec'])

if __name__ == "__main__":
    main()
