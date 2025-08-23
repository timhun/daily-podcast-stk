# scripts/data_collector.py
import yfinance as yf
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
import sys
from utils import setup_json_logger, get_taiwan_time, slack_alert

logger = setup_json_logger('data_collector')

def main(mode=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    symbols = config['symbols'][mode] if mode else config['symbols']['tw'] + config['symbols']['us']
    os.makedirs('data', exist_ok=True)
    
    for source in config['data_sources']:
        if not source['enabled']:
            continue
        for symbol in symbols:
            for attempt in range(config['retry_times']):
                try:
                    daily_data = yf.download(symbol, period=f"{config['data_retention_days']}d", interval="1d")
                    if daily_data.empty or daily_data['Close'].isna().any():
                        raise ValueError("Invalid data")
                    daily_file = f"data/daily_{symbol.replace('.', '_').replace('^', '')}.csv"
                    daily_data.to_csv(daily_file)
                    logger.info(json.dumps({"symbol": symbol, "type": "daily", "rows": len(daily_data)}))
                    
                    hourly_data = yf.download(symbol, period=f"{config['hourly_retention_days']}d", interval="1h")
                    if hourly_data.empty or hourly_data['Close'].isna().any():
                        raise ValueError("Invalid data")
                    hourly_file = f"data/hourly_{symbol.replace('.', '_').replace('^', '')}.csv"
                    hourly_data.to_csv(hourly_file)
                    logger.info(json.dumps({"symbol": symbol, "type": "hourly", "rows": len(hourly_data)}))
                    
                    time.sleep(config['delay_sec'])
                    break
                except Exception as e:
                    logger.error(json.dumps({"symbol": symbol, "attempt": attempt, "error": str(e)}))
                    if attempt == config['retry_times'] - 1:
                        slack_alert(f"Data collection failed for {symbol}: {e}")
                    time.sleep(config['delay_sec'])

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['us', 'tw'] else None
    main(mode)
