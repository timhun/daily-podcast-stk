"""
數據收集智士 (Data Intelligence Agent)
負責從各種來源收集市場數據和新聞資訊
"""

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import aiohttp
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
        # 簡化數據目錄結構
        self.data_dir = Path("data/market")
        self.news_dir = Path("data/news")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.news_dir.mkdir(parents=True, exist_ok=True)
        
        # 創建今天的新聞目錄（新聞還是按日期分組）
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
        
        Args:
            symbol: 股票代號
            period: 時間範圍 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 數據間隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            logger.info(f"正在獲取 {symbol} 的 {interval} 數據，範圍: {period}")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"{symbol} 沒有獲取到數據")
                return None
            
            # 添加股票代號和更新時間欄位
            data['Symbol'] = symbol
            data['Updated'] = get_taiwan_time().isoformat()
            
            # 重設索引，將日期作為欄位
            data.reset_index(inplace=True)
            
            # 重新排序欄位，讓時間欄位在前面
            columns = ['Datetime', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume', 'Updated']
            if 'Dividends' in data.columns:
                columns.insert(-1, 'Dividends')
            if 'Stock Splits' in data.columns:
                columns.insert(-1, 'Stock Splits')
            
            data = data[columns]
            
            logger.success(f"成功獲取 {symbol} 數據，共 {len(data)} 筆記錄")
            return data
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 數據失敗: {str(e)}")
            raise
    
    def save_market_data(self, data: pd.DataFrame, symbol: str, data_type: str) -> bool:
        """
        儲存市場數據到簡化的檔案結構
        
        Args:
            data: DataFrame
            symbol: 股票代號
            data_type: "daily" 或 "hourly"
        """
        try:
            # 清理符號名稱作為檔案名
            clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')
            filename = self.data_dir / f"{data_type}_{clean_symbol}.csv"
            
            # 如果檔案已存在，檢查是否需要更新
            if filename.exists():
                try:
                    existing_data = pd.read_csv(filename)
                    existing_data['Datetime'] = pd.to_datetime(existing_data['Datetime'])
                    data['Datetime'] = pd.to_datetime(data['Datetime'])
                    
                    # 合併新舊數據，去重並排序
                    combined_data = pd.concat([existing_data, data]).drop_duplicates(
                        subset=['Datetime'], keep='last'
                    ).sort_values('Datetime').reset_index(drop=True)
                    
                    # 根據數據類型保留適當的記錄數量
                    if data_type == "daily":
                        # 保留最近300天
                        combined_data = combined_data.tail(300)
                    elif data_type == "hourly":
                        # 保留最近14天的數據
                        cutoff_date = get_taiwan_time() - timedelta(days=14)
                        combined_data = combined_data[combined_data['Datetime'] >= cutoff_date]
                    
                    data_to_save = combined_data
                    
                except Exception as e:
                    logger.warning(f"合併 {symbol} 歷史數據時出錯，使用新數據: {str(e)}")
                    data_to_save = data
            else:
                data_to_save = data
            
            # 儲存數據
            data_to_save.to_csv(filename, index=False, encoding='utf-8')
            logger.success(f"已儲存 {symbol} {data_type} 數據到 {filename} (共 {len(data_to_save)} 筆)")
            return True
            
        except Exception as e:
            logger.error(f"儲存 {symbol} {data_type} 數據失敗: {str(e)}")
            return False
    
    def collect_taiwan_stocks(self) -> Dict[str, int]:
        """收集台股數據"""
        symbols = self.config.get("markets.taiwan.symbols", [])
        logger.info(f"開始收集台股數據，共 {len(symbols)} 支股票")
        
        results = {'daily': 0, 'hourly': 0, 'errors': 0}
        
        for symbol in symbols:
            try:
                # 收集日線數據
                daily_data = self.fetch_yahoo_data(symbol, period="1y", interval="1d")
                if daily_data is not None and validate_data_quality(daily_data, symbol):
                    if self.save_market_data(daily_data, symbol, "daily"):
                        results['daily'] += 1
                
                # 收集小時線數據
                hourly_data = self.fetch_yahoo_data(symbol, period="1mo", interval="1h")
                if hourly_data is not None and validate_data_quality(hourly_data, symbol, min_rows=5):
                    if self.save_market_data(hourly_data, symbol, "hourly"):
                        results['hourly'] += 1
                
            except Exception as e:
                logger.error(f"收集 {symbol} 數據時發生錯誤: {str(e)}")
                results['errors'] += 1
                continue
        
        logger.info(f"台股數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {results['errors']}")
        return results
    
    def collect_us_stocks(self) -> Dict[str, int]:
        """收集美股數據"""
        symbols = self.config.get("markets.us.symbols", [])
        logger.info(f"開始收集美股數據，共 {len(symbols)} 支股票")
        
        results = {'daily': 0, 'hourly': 0, 'errors': 0}
        
        for symbol in symbols:
            try:
                # 收集日線數據
                daily_data = self.fetch_yahoo_data(symbol, period="1y", interval="1d")
                if daily_data is not None and validate_data_quality(daily_data, symbol):
                    if self.save_market_data(daily_data, symbol, "daily"):
                        results['daily'] += 1
                
                # 收集小時線數據
                hourly_data = self.fetch_yahoo_data(symbol, period="1mo", interval="1h")
                if hourly_data is not None and validate_data_quality(hourly_data, symbol, min_rows=5):
                    if self.save_market_data(hourly_data, symbol, "hourly"):
                        results['hourly'] += 1
                
            except Exception as e:
                logger.error(f"收集 {symbol} 數據時發生錯誤: {str(e)}")
                results['errors'] += 1
                continue
        
        logger.info(f"美股數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {results['errors']}")
        return results
    
    def collect_crypto_data(self) -> Dict[str, int]:
        """收集加密貨幣數據"""
        symbols = self.config.get("markets.crypto.symbols", [])
        logger.info(f"開始收集加密貨幣數據，共 {len(symbols)} 種")
        
        results = {'daily': 0, 'hourly': 0, 'errors': 0}
        
        for symbol in symbols:
            try:
                # 收集日線數據
                daily_data = self.fetch_yahoo_data(symbol, period="6mo", interval="1d")
                if daily_data is not None and validate_data_quality(daily_data, symbol):
                    if self.save_market_data(daily_data, symbol, "daily"):
                        results['daily'] += 1
                
                # 收集小時線數據
                hourly_data = self.fetch_yahoo_data(symbol, period="1mo", interval="1h")
                if hourly_data is not None and validate_data_quality(hourly_data, symbol, min_rows=5):
                    if self.save_market_data(hourly_data, symbol, "hourly"):
                        results['hourly'] += 1
                
            except Exception as e:
                logger.error(f"收集 {symbol} 數據時發生錯誤: {str(e)}")
                results['errors'] += 1
                continue
        
        logger.info(f"加密貨幣數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {results['errors']}")
        return results


class NewsDataCollector:
    """新聞數據收集器"""
    
    def __init__(self):
        self.config = config_manager
        self.news_dir = Path("data/news")
        self.news_dir.mkdir(parents=True, exist_ok=True)
        
        self.today = get_taiwan_time().strftime("%Y-%m-%d")
        self.today_dir = self.news_dir / self.today
        self.today_dir.mkdir(exist_ok=True)
    
    @retry_on_failure(max_retries=3, delay=2.0)
    def fetch_rss_news(self, rss_url: str, max_items: int = 10) -> List[Dict]:
        """
        從 RSS 獲取新聞
        
        Args:
            rss_url: RSS 網址
            max_items: 最大新聞數量
        """
        try:
            logger.info(f"正在獲取 RSS 新聞: {rss_url}")
            
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                logger.warning(f"RSS feed 可能有格式問題: {rss_url}")
            
            news_items = []
            for entry in feed.entries[:max_items]:
                news_item = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'source': feed.feed.get('title', 'Unknown'),
                    'collected_at': get_taiwan_time().isoformat()
                }
                news_items.append(news_item)
            
            logger.success(f"成功獲取 {len(news_items)} 則新聞")
            return news_items
            
        except Exception as e:
            logger.error(f"獲取 RSS 新聞失敗: {str(e)}")
            raise
    
    def collect_taiwan_news(self) -> int:
        """收集台股相關新聞"""
        news_sources = self.config.get("markets.taiwan.news_sources", [])
        all_news = []
        
        for source_url in news_sources:
            try:
                news = self.fetch_rss_news(source_url, max_items=5)
                all_news.extend(news)
            except Exception as e:
                logger.error(f"收集台股新聞失敗 {source_url}: {str(e)}")
                continue
        
        if all_news:
            # 儲存新聞數據
            import json
            filename = self.today_dir / "taiwan_news.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_news, f, ensure_ascii=False, indent=2)
            logger.success(f"已儲存 {len(all_news)} 則台股新聞到 {filename}")
        
        return len(all_news)
    
    def collect_us_news(self) -> int:
        """收集美股相關新聞"""
        news_sources = self.config.get("markets.us.news_sources", [])
        all_news = []
        
        for source_url in news_sources:
            try:
                news = self.fetch_rss_news(source_url, max_items=5)
                all_news.extend(news)
            except Exception as e:
                logger.error(f"收集美股新聞失敗 {source_url}: {str(e)}")
                continue
        
        if all_news:
            import json
            filename = self.today_dir / "us_news.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_news, f, ensure_ascii=False, indent=2)
            logger.success(f"已儲存 {len(all_news)} 則美股新聞到 {filename}")
        
        return len(all_news)


class DataCollector:
    """主數據收集器"""
    
    def __init__(self):
        self.market_collector = MarketDataCollector()
        self.news_collector = NewsDataCollector()
    
    def collect_all_data(self, market: str = "all") -> Dict:
        """
        收集所有數據
        
        Args:
            market: "all", "taiwan", "us", "crypto"
        """
        logger.info(f"開始數據收集任務，市場範圍: {market}")
        start_time = get_taiwan_time()
        
        results = {
            'market_data': {},
            'news_data': {},
            'collection_time': start_time.isoformat(),
            'status': 'success',
            'summary': {}
        }
        
        try:
            total_files = 0
            
            # 收集市場數據
            if market in ["all", "taiwan"]:
                logger.info("收集台股數據...")
                taiwan_data = self.market_collector.collect_taiwan_stocks()
                results['market_data']['taiwan'] = taiwan_data
                total_files += taiwan_data['daily'] + taiwan_data['hourly']
                
                logger.info("收集台股新聞...")
                taiwan_news_count = self.news_collector.collect_taiwan_news()
                results['news_data']['taiwan'] = taiwan_news_count
            
            if market in ["all", "us"]:
                logger.info("收集美股數據...")
                us_data = self.market_collector.collect_us_stocks()
                results['market_data']['us'] = us_data
                total_files += us_data['daily'] + us_data['hourly']
                
                logger.info("收集美股新聞...")
                us_news_count = self.news_collector.collect_us_news()
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
        
        # 只清理新聞數據（按日期分組）
        # 市場數據檔案現在是直接更新，不需要按日期清理
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
        
        # 找最新更新時間
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
        # 測試模式下只收集少量數據
        test_symbol = "^TWII" if args.market == "taiwan" else "^GSPC"
        data = collector.market_collector.fetch_yahoo_data(test_symbol)
        if data is not None:
            logger.success(f"測試成功！獲取到 {len(data)} 筆 {test_symbol} 數據")
        else:
            logger.error("測試失敗！")
            sys.exit(1)
    else:
        # 正常模式
        results = collector.collect_all_data(args.market)
        
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
