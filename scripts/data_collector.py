"""
數據收集智士 (Data Intelligence Agent)
負責從 Yahoo Finance 收集市場數據
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import sys
import time
from utils import ConfigManager, setup_json_logger, retry_on_failure, get_taiwan_time, validate_data_quality

# Initialize logger and config
logger = setup_json_logger("data_collector")
config_manager = ConfigManager()

class MarketDataCollector:
    """市場數據收集器"""
    
    def __init__(self):
        self.config = config_manager
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    @retry_on_failure(max_retries=config_manager.get('retry_times', 5), delay=config_manager.get('delay_sec', 5))
    def fetch_yahoo_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        從 Yahoo Finance 獲取股票數據
        """
        try:
            logger.info(json.dumps({"symbol": symbol, "interval": interval, "period": period, "status": "fetching"}))
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(json.dumps({"symbol": symbol, "status": "empty"}))
                return None
            
            data['Symbol'] = symbol
            data.reset_index(inplace=True)
            logger.info(json.dumps({"symbol": symbol, "status": "fetched", "rows": len(data)}))
            return data
        except Exception as e:
            logger.error(json.dumps({"symbol": symbol, "error": str(e)}))
            raise
    
    def collect_market_data(self, symbols: list, market: str) -> dict:
        """收集指定市場的數據"""
        logger.info(json.dumps({"market": market, "symbols_count": len(symbols), "status": "collecting"}))
        results = {}
        
        for symbol in symbols:
            try:
                # Daily data (300 days)
                daily_data = self.fetch_yahoo_data(symbol, period="1y", interval="1d")
                if daily_data is not None and validate_data_quality(daily_data, symbol, min_rows=200):
                    if len(daily_data) > 300:
                        daily_data = daily_data.tail(300)
                    clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_')
                    filename = self.data_dir / f"daily_{clean_symbol}.csv"
                    daily_data.to_csv(filename, index=False, encoding='utf-8')
                    logger.info(json.dumps({"symbol": symbol, "file": str(filename), "status": "saved"}))
                    results[f"daily_{symbol}"] = daily_data
                
                # Hourly data (14 days)
                hourly_data = self.fetch_yahoo_data(symbol, period="1mo", interval="1h")
                if hourly_data is not None and validate_data_quality(hourly_data, symbol, min_rows=5):
                    cutoff_date = get_taiwan_time() - timedelta(days=14)
                    hourly_data = hourly_data[hourly_data['Datetime'] >= cutoff_date]
                    filename = self.data_dir / f"hourly_{clean_symbol}.csv"
                    hourly_data.to_csv(filename, index=False, encoding='utf-8')
                    logger.info(json.dumps({"symbol": symbol, "file": str(filename), "status": "saved"}))
                    results[f"hourly_{symbol}"] = hourly_data
            except Exception as e:
                logger.error(json.dumps({"symbol": symbol, "error": str(e)}))
                continue
        
        return results
    
    def collect_all_data(self, mode: str = "all") -> dict:
        """收集所有市場數據"""
        logger.info(json.dumps({"mode": mode, "status": "starting"}))
        start_time = get_taiwan_time()
        results = {'status': 'success', 'collection_time': start_time.isoformat()}
        
        try:
            if mode == "all":
                symbols = self.config.get('symbols.tw', []) + self.config.get('symbols.us', [])
                results['market_data'] = self.collect_market_data(symbols, "all")
            elif mode == "us":
                results['market_data'] = self.collect_market_data(self.config.get('symbols.us', []), "us")
            elif mode == "tw":
                results['market_data'] = self.collect_market_data(self.config.get('symbols.tw', []), "tw")
            
            end_time = get_taiwan_time()
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            results['completion_time'] = end_time.isoformat()
        except Exception as e:
            logger.error(json.dumps({"error": str(e)}))
            results['status'] = 'error'
            results['error_message'] = str(e)
        
        return results
    
    def cleanup_old_data(self, retention_days: int = 30):
        """清理舊數據（交由 upload_manager 負責）"""
        logger.info(json.dumps({"status": "cleanup_skipped", "message": "Cleanup handled by upload_manager"}))
        pass

def main():
    parser = argparse.ArgumentParser(description="數據收集智士")
    parser.add_argument(
        "--mode", 
        choices=["all", "us", "tw"],
        default="all",
        help="指定收集的市場數據 (us, tw, all)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="執行舊數據清理"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="測試模式（只收集單一股票數據）"
    )
    
    args = parser.parse_args()
    logger.info(json.dumps({"status": "starting", "args": vars(args)}))
    
    collector = MarketDataCollector()
    
    if args.cleanup:
        collector.cleanup_old_data()
        return
    
    if args.test:
        logger.info(json.dumps({"mode": "test", "symbol": "^TWII" if args.mode == "tw" else "^GSPC"}))
        test_symbol = "^TWII" if args.mode == "tw" else "^GSPC"
        data = collector.fetch_yahoo_data(test_symbol)
        if data is not None:
            logger.info(json.dumps({"symbol": test_symbol, "status": "test_success", "rows": len(data)}))
        else:
            logger.error(json.dumps({"symbol": test_symbol, "status": "test_failed"}))
            sys.exit(1)
    else:
        results = collector.collect_all_data(args.mode)
        if results['status'] == 'success':
            logger.info(json.dumps({"status": "completed", "duration": results['duration_seconds']}))
        else:
            logger.error(json.dumps({"status": "failed", "error": results.get('error_message', 'Unknown')}))
            sys.exit(1)

if __name__ == "__main__":
    main()