import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import aiohttp
import json  # 新增導入
from typing import List, Dict, Optional, Tuple
import argparse
import sys

# 導入我們的工具函數
from utils import (
    config_manager, 
    LoggerSetup, 
    retry_on_failure, 
    get_taiwan_time,
    validate_data_quality
)
from loguru import logger

# 設定日誌
LoggerSetup.setup_logger("data_collector", config_manager.get("system.log_level", "INFO"))

class MarketDataCollector:
    """市場數據收集器"""
    
    def __init__(self):
        self.config = config_manager
        self.data_dir = Path("data/market")
        self.news_dir = Path("data/news")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.news_dir.mkdir(parents=True, exist_ok=True)
        
        self.today = get_taiwan_time().strftime("%Y-%m-%d")
        self.today_news_dir = self.news_dir / self.today
        self.today_news_dir.mkdir(exist_ok=True)
    
    @retry_on_failure(max_retries=3, delay=3.0)
    def fetch_yahoo_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        從 Yahoo Finance 獲取股票數據
        """
        try:
            logger.info(f"正在獲取 {symbol} 的 {interval} 數據，範圍: {period}")
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"{symbol} 沒有獲取到數據")
                return None
            
            data['Symbol'] = symbol
            data['Updated'] = get_taiwan_time().isoformat()
            data.reset_index(inplace=True)
            
            if 'Date' in data.columns:
                data.rename(columns={'Date': 'Datetime'}, inplace=True)
            
            required_columns = ['Datetime', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                logger.error(f"{symbol} 缺少必要欄位: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            columns = ['Datetime', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume', 'Updated']
            optional_columns = ['Dividends', 'Stock Splits']
            for col in optional_columns:
                if col in data.columns:
                    columns.insert(-1, col)
            
            available_columns = [col for col in columns if col in data.columns]
            data = data[available_columns]
            
            logger.success(f"成功獲取 {symbol} 數據，共 {len(data)} 筆記錄")
            return data
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 數據失敗: {str(e)}")
            raise
    
    def save_market_data(self, data: pd.DataFrame, symbol: str, data_type: str) -> bool:
        """
        儲存市場數據到簡化的檔案結構
        """
        try:
            clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')
            filename = self.data_dir / f"{data_type}_{clean_symbol}.csv"
            
            if filename.exists():
                try:
                    existing_data = pd.read_csv(filename)
                    existing_data['Datetime'] = pd.to_datetime(existing_data['Datetime'])
                    data['Datetime'] = pd.to_datetime(data['Datetime'])
                    combined_data = pd.concat([existing_data, data]).drop_duplicates(
                        subset=['Datetime'], keep='last'
                    ).sort_values('Datetime').reset_index(drop=True)
                    
                    if data_type == "daily":
                        combined_data = combined_data.tail(300)
                    elif data_type == "hourly":
                        cutoff_date = get_taiwan_time() - timedelta(days=14)
                        combined_data = combined_data[combined_data['Datetime'] >= cutoff_date]
                    
                    data_to_save = combined_data
                except Exception as e:
                    logger.warning(f"合併 {symbol} 歷史數據時出錯，使用新數據: {str(e)}")
                    data_to_save = data
            else:
                data_to_save = data
            
            data_to_save.to_csv(filename, index=False)
            logger.info(f"成功儲存 {symbol} 的 {data_type} 數據到 {filename}")
            return True
            
        except Exception as e:
            logger.error(f"儲存 {symbol} 的 {data_type} 數據失敗: {str(e)}")
            return False
    
    async def fetch_news(self, url: str, category: str) -> List[Dict]:
        """異步抓取新聞 RSS"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, timeout=10) as response:
                    text = await response.text()
                    feed = feedparser.parse(text)
                    
                    news_items = []
                    for entry in feed.entries[:self.config.get("data_collection.news_limit", 3)]:
                        news_items.append({
                            'title': entry.get('title', ''),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', ''),
                            'category': category
                        })
                    
                    return news_items
                    
        except Exception as e:
            logger.error(f"抓取新聞 RSS 失敗 ({url}): {str(e)}")
            return []

class NewsCollector:
    """新聞收集器"""
    
    def __init__(self, market_collector: MarketDataCollector):
        self.market_collector = market_collector
        self.config = market_collector.config
    
    async def collect_taiwan_news(self) -> int:
        """收集台股新聞"""
        news_urls = self.config.get("markets.taiwan.news_sources", [])
        categories = self.config.get("news_categories", ["經濟", "半導體"])
        news_count = 0
        
        for url in news_urls:
            for category in categories:
                try:
                    news_items = await self.market_collector.fetch_news(url, category)
                    for item in news_items:
                        filename = self.market_collector.today_news_dir / f"news_taiwan_{news_count}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(item, f, ensure_ascii=False, indent=2)
                        news_count += 1
                        logger.info(f"保存台股新聞: {filename}")
                except Exception as e:
                    logger.error(f"處理新聞 {url} (類別: {category}) 失敗: {str(e)}")
        
        logger.info(f"共收集 {news_count} 篇台股新聞")
        return news_count
    
    async def collect_us_news(self) -> int:
        """收集美股新聞"""
        news_urls = self.config.get("markets.us.news_sources", [])
        categories = self.config.get("news_categories", ["經濟", "半導體"])
        news_count = 0
        
        for url in news_urls:
            for category in categories:
                try:
                    news_items = await self.market_collector.fetch_news(url, category)
                    for item in news_items:
                        filename = self.market_collector.today_news_dir / f"news_us_{news_count}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(item, f, ensure_ascii=False, indent=2)
                        news_count += 1
                        logger.info(f"保存美股新聞: {filename}")
                except Exception as e:
                    logger.error(f"處理新聞 {url} (類別: {category}) 失敗: {str(e)}")
        
        logger.info(f"共收集 {news_count} 篇美股新聞")
        return news_count

class DataCollector:
    """整體數據收集協調器"""
    
    def __init__(self):
        self.market_collector = MarketDataCollector()
        self.news_collector = NewsCollector(self.market_collector)
    
    async def collect_all_data(self, market: str = "all") -> Dict:
        """收集所有指定市場的數據"""
        results = {
            'status': 'success',
            'market_data': {'taiwan': {}, 'us': {}, 'crypto': {}},
            'news_data': {'taiwan': 0, 'us': 0},
            'summary': {'total_market_files': 0},
            'error_message': None
        }
        
        start_time = get_taiwan_time()
        total_files = 0
        
        try:
            if market in ["all", "taiwan"]:
                logger.info("收集台股數據...")
                taiwan_data = self.market_collector.collect_taiwan_stocks()
                results['market_data']['taiwan'] = taiwan_data
                total_files += taiwan_data['daily'] + taiwan_data['hourly']
                
                logger.info("收集台股新聞...")
                taiwan_news_count = await self.news_collector.collect_taiwan_news()
                results['news_data']['taiwan'] = taiwan_news_count
            
            if market in ["all", "us"]:
                logger.info("收集美股數據...")
                us_data = self.market_collector.collect_us_stocks()
                results['market_data']['us'] = us_data
                total_files += us_data['daily'] + us_data['hourly']
                
                logger.info("收集美股新聞...")
                us_news_count = await self.news_collector.collect_us_news()
                results['news_data']['us'] = us_news_count
            
            if market in ["all", "crypto"]:
                logger.info("收集加密貨幣數據...")
                crypto_data = self.market_collector.collect_crypto_data()
                results['market_data']['crypto'] = crypto_data
                total_files += crypto_data['daily'] + crypto_data['hourly']
            
            end_time = get_taiwan_time()
            duration = (end_time - start_time).total_seconds()
            
            results['duration_seconds'] = duration
            results['completion_time'] = end_time.isoformat()
            results['summary']['total_market_files'] = total_files
            
            logger.success(f"數據收集完成，耗時 {duration:.2f} 秒，共處理 {total_files} 個市場數據檔案")
            
        except Exception as e:
            logger.error(f"數據收集過程中發生錯誤: {str(e)}")
            results['status'] = 'error'
            results['error_message'] = str(e)
        
        return results
    
    def cleanup_old_data(self, retention_days: int = 30):
        """清理舊數據"""
        logger.info(f"開始清理 {retention_days} 天前的舊數據")
        
        cutoff_date = get_taiwan_time() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        news_dir = Path("data/news")
        if news_dir.exists():
            cleaned_dirs = 0
            for date_dir in news_dir.iterdir():
                if date_dir.is_dir() and date_dir.name < cutoff_str:
                    import shutil
                    shutil.rmtree(date_dir)
                    cleaned_dirs += 1
                    logger.info(f"已刪除舊新聞目錄: {date_dir}")
            
            if cleaned_dirs == 0:
                logger.info("沒有需要清理的舊新聞數據")
            else:
                logger.success(f"已清理 {cleaned_dirs} 個舊新聞目錄")
    
    def get_data_status(self) -> Dict:
        """獲取數據狀態統計"""
        data_dir = Path("data/market")
        news_dir = Path("data/news")
        
        status = {
            'market_files': {
                'daily': 0,
                'hourly': 0,
                'total': 0
            },
            'news_dirs': 0,
            'last_updated': None
        }
        
        if data_dir.exists():
            for file in data_dir.glob("*.csv"):
                if file.name.startswith("daily_"):
                    status['market_files']['daily'] += 1
                elif file.name.startswith("hourly_"):
                    status['market_files']['hourly'] += 1
                status['market_files']['total'] += 1
        
        if news_dir.exists():
            status['news_dirs'] = len([d for d in news_dir.iterdir() if d.is_dir()])
        
        if data_dir.exists():
            csv_files = list(data_dir.glob("*.csv"))
            if csv_files:
                latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
                status['last_updated'] = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
        
        return status

def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(description="數據收集智士")
    parser.add_argument(
        "--market", 
        choices=["all", "taiwan", "us", "crypto"],
        default="all",
        help="指定收集的市場數據"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="執行舊數據清理"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="測試模式（只收集少量數據）"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="顯示數據狀態"
    )
    
    args = parser.parse_args()
    
    logger.info("=== 數據收集智士啟動 ===")
    
    collector = DataCollector()
    
    if args.status:
        status = collector.get_data_status()
        logger.info("數據狀態統計:")
        logger.info(f"  市場數據檔案: {status['market_files']['total']} 個 (日線: {status['market_files']['daily']}, 小時線: {status['market_files']['hourly']})")
        logger.info(f"  新聞目錄: {status['news_dirs']} 個")
        if status['last_updated']:
            logger.info(f"  最後更新: {status['last_updated']}")
        return
    
    if args.cleanup:
        collector.cleanup_old_data()
    
    if args.test:
        logger.info("測試模式：只收集單一股票數據")
        test_symbol = "^TWII" if args.market == "taiwan" else "^GSPC"
        data = collector.market_collector.fetch_yahoo_data(test_symbol)
        if data is not None:
            logger.success(f"測試成功！獲取到 {len(data)} 筆 {test_symbol} 數據")
        else:
            logger.error("測試失敗！")
            sys.exit(1)
    else:
        results = asyncio.run(collector.collect_all_data(args.market))
        
        if results['status'] == 'success':
            logger.success("✅ 數據收集任務完成！")
            if 'summary' in results:
                logger.info(f"📊 處理統計: {results['summary']}")
        else:
            logger.error("❌ 數據收集任務失敗！")
            sys.exit(1)
    
    logger.info("=== 數據收集智士結束 ===")

if __name__ == "__main__":
    main()


