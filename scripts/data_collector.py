import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Tuple
import argparse
import sys

# 導入我們的工具函數
from utils import (
    config_manager, 
    LoggerSetup, 
    retry_on_failure, 
    get_taiwan_time,
    validate_data_quality,
    get_clean_symbol
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
            clean_symbol = get_clean_symbol(symbol)
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
    
    def collect_taiwan_stocks(self) -> Dict:
        """收集台股數據"""
        logger.info("開始收集台股數據...")
        symbols = self.config.get("markets.taiwan.symbols", {})
        results = {"daily": 0, "hourly": 0, "errors": []}
        
        # 收集日線數據
        daily_symbols = symbols.get("daily", [])
        logger.info(f"收集 {len(daily_symbols)} 個台股日線數據")
        
        for symbol in daily_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="300d", interval="1d")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "daily"):
                        results["daily"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 數據品質不合格")
            except Exception as e:
                logger.error(f"處理台股 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: {str(e)}")
        
        # 收集小時線數據
        hourly_symbols = symbols.get("hourly", [])
        logger.info(f"收集 {len(hourly_symbols)} 個台股小時線數據")
        
        for symbol in hourly_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="60d", interval="1h")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "hourly"):
                        results["hourly"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 小時線儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 小時線數據品質不合格")
            except Exception as e:
                logger.error(f"處理台股小時線 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: 小時線 {str(e)}")
        
        logger.info(f"台股數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {len(results['errors'])}")
        return results
    
    def collect_us_stocks(self) -> Dict:
        """收集美股數據"""
        logger.info("開始收集美股數據...")
        symbols = self.config.get("markets.us.symbols", {})
        results = {"daily": 0, "hourly": 0, "errors": []}
        
        # 收集日線數據
        daily_symbols = symbols.get("daily", [])
        logger.info(f"收集 {len(daily_symbols)} 個美股日線數據")
        
        for symbol in daily_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="300d", interval="1d")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "daily"):
                        results["daily"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 數據品質不合格")
            except Exception as e:
                logger.error(f"處理美股 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: {str(e)}")
        
        # 收集小時線數據
        hourly_symbols = symbols.get("hourly", [])
        logger.info(f"收集 {len(hourly_symbols)} 個美股小時線數據")
        
        for symbol in hourly_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="60d", interval="1h")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "hourly"):
                        results["hourly"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 小時線儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 小時線數據品質不合格")
            except Exception as e:
                logger.error(f"處理美股小時線 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: 小時線 {str(e)}")
        
        logger.info(f"美股數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {len(results['errors'])}")
        return results
    
    def collect_crypto_data(self) -> Dict:
        """收集加密貨幣數據"""
        logger.info("開始收集加密貨幣數據...")
        symbols = self.config.get("markets.crypto.symbols", {})
        results = {"daily": 0, "hourly": 0, "errors": []}
        
        # 收集日線數據
        daily_symbols = symbols.get("daily", [])
        logger.info(f"收集 {len(daily_symbols)} 個加密貨幣日線數據")
        
        for symbol in daily_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="300d", interval="1d")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "daily"):
                        results["daily"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 數據品質不合格")
            except Exception as e:
                logger.error(f"處理加密貨幣 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: {str(e)}")
        
        # 收集小時線數據
        hourly_symbols = symbols.get("hourly", [])
        logger.info(f"收集 {len(hourly_symbols)} 個加密貨幣小時線數據")
        
        for symbol in hourly_symbols:
            try:
                data = self.fetch_yahoo_data(symbol, period="60d", interval="1h")
                if data is not None and validate_data_quality(data, symbol):
                    if self.save_market_data(data, symbol, "hourly"):
                        results["hourly"] += 1
                    else:
                        results["errors"].append(f"{symbol}: 小時線儲存失敗")
                else:
                    results["errors"].append(f"{symbol}: 小時線數據品質不合格")
            except Exception as e:
                logger.error(f"處理加密貨幣小時線 {symbol} 失敗: {e}")
                results["errors"].append(f"{symbol}: 小時線 {str(e)}")
        
        logger.info(f"加密貨幣數據收集完成 - 日線: {results['daily']}, 小時線: {results['hourly']}, 錯誤: {len(results['errors'])}")
        return results
    
    async def fetch_news(self, url: str, category: str) -> List[Dict]:
        """異步抓取新聞 RSS"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, timeout=30) as response:
                    text = await response.text()
                    feed = feedparser.parse(text)
                    
                    news_items = []
                    max_items = self.config.get("data_collection.news_limit", 5)
                    
                    for entry in feed.entries[:max_items]:
                        news_items.append({
                            'title': entry.get('title', ''),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', ''),
                            'category': category,
                            'collected_at': get_taiwan_time().isoformat()
                        })
                    
                    logger.info(f"成功抓取 {len(news_items)} 則新聞 (類別: {category})")
                    return news_items
                    
        except Exception as e:
            logger.error(f"抓取新聞 RSS 失敗 ({url}): {str(e)}")
            return []

class NewsCollector:
    """新聞收集器"""
    
    def __init__(self, market_collector: MarketDataCollector):
        self.market_collector = market_collector
        self.config = market_collector.config
    
    async def collect_news_for_market(self, market: str, news_sources: List[str]) -> int:
        """通用新聞收集方法"""
        news_count = 0
        
        for url in news_sources:
            try:
                # 簡化分類處理，每個URL收集一次新聞
                news_items = await self.market_collector.fetch_news(url, market)
                
                for i, item in enumerate(news_items):
                    filename = self.market_collector.today_news_dir / f"news_{market}_{news_count:03d}.json"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(item, f, ensure_ascii=False, indent=2)
                    
                    news_count += 1
                    logger.debug(f"保存 {market} 新聞: {filename}")
                    
            except Exception as e:
                logger.error(f"處理 {market} 新聞 {url} 失敗: {str(e)}")
        
        logger.info(f"共收集 {news_count} 篇 {market} 新聞")
        return news_count
    
    async def collect_taiwan_news(self) -> int:
        """收集台股新聞"""
        news_sources = self.config.get("markets.taiwan.news_sources", [])
        return await self.collect_news_for_market("taiwan", news_sources)
    
    async def collect_us_news(self) -> int:
        """收集美股新聞"""
        news_sources = self.config.get("markets.us.news_sources", [])
        return await self.collect_news_for_market("us", news_sources)

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
            'summary': {'total_market_files': 0, 'total_news': 0, 'total_errors': 0},
            'error_message': None,
            'errors': []
        }
        
        start_time = get_taiwan_time()
        total_files = 0
        total_news = 0
        all_errors = []
        
        try:
            if market in ["all", "taiwan"]:
                logger.info("收集台股數據...")
                taiwan_data = self.market_collector.collect_taiwan_stocks()
                results['market_data']['taiwan'] = taiwan_data
                total_files += taiwan_data['daily'] + taiwan_data['hourly']
                all_errors.extend(taiwan_data.get('errors', []))
                
                logger.info("收集台股新聞...")
                taiwan_news_count = await self.news_collector.collect_taiwan_news()
                results['news_data']['taiwan'] = taiwan_news_count
                total_news += taiwan_news_count
            
            if market in ["all", "us"]:
                logger.info("收集美股數據...")
                us_data = self.market_collector.collect_us_stocks()
                results['market_data']['us'] = us_data
                total_files += us_data['daily'] + us_data['hourly']
                all_errors.extend(us_data.get('errors', []))
                
                logger.info("收集美股新聞...")
                us_news_count = await self.news_collector.collect_us_news()
                results['news_data']['us'] = us_news_count
                total_news += us_news_count
            
            if market in ["all", "crypto"]:
                logger.info("收集加密貨幣數據...")
                crypto_data = self.market_collector.collect_crypto_data()
                results['market_data']['crypto'] = crypto_data
                total_files += crypto_data['daily'] + crypto_data['hourly']
                all_errors.extend(crypto_data.get('errors', []))
            
            end_time = get_taiwan_time()
            duration = (end_time - start_time).total_seconds()
            
            results['duration_seconds'] = duration
            results['completion_time'] = end_time.isoformat()
            results['summary']['total_market_files'] = total_files
            results['summary']['total_news'] = total_news
            results['summary']['total_errors'] = len(all_errors)
            results['errors'] = all_errors
            
            # 如果有錯誤但仍有成功收集的數據，標記為部分成功
            if all_errors and total_files > 0:
                results['status'] = 'partial_success'
                logger.warning(f"數據收集部分成功，共 {len(all_errors)} 個錯誤")
            elif all_errors and total_files == 0:
                results['status'] = 'error'
                results['error_message'] = f"數據收集失敗，共 {len(all_errors)} 個錯誤"
            
            logger.success(f"數據收集完成，耗時 {duration:.2f} 秒，處理 {total_files} 個市場數據檔案，{total_news} 則新聞")
            
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
            'last_updated': None,
            'data_health': 'unknown'
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
                
                # 檢查數據健康狀態
                now = get_taiwan_time()
                last_update = datetime.fromtimestamp(latest_file.stat().st_mtime)
                hours_since_update = (now - last_update).total_seconds() / 3600
                
                if hours_since_update < 6:
                    status['data_health'] = 'healthy'
                elif hours_since_update < 24:
                    status['data_health'] = 'warning'
                else:
                    status['data_health'] = 'stale'
        
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="啟用調試模式"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.remove()
        LoggerSetup.setup_logger("data_collector", "DEBUG")
    
    logger.info("=== 數據收集智士啟動 ===")
    
    collector = DataCollector()
    
    if args.status:
        status = collector.get_data_status()
        logger.info("數據狀態統計:")
        logger.info(f"  市場數據檔案: {status['market_files']['total']} 個 (日線: {status['market_files']['daily']}, 小時線: {status['market_files']['hourly']})")
        logger.info(f"  新聞目錄: {status['news_dirs']} 個")
        logger.info(f"  數據健康狀態: {status['data_health']}")
        if status['last_updated']:
            logger.info(f"  最後更新: {status['last_updated']}")
        return
    
    if args.cleanup:
        retention_days = config_manager.get("data_collection.data_retention_days", 30)
        collector.cleanup_old_data(retention_days)
    
    if args.test:
        logger.info("測試模式：只收集單一股票數據")
        test_symbol = "0050.TW" if args.market in ["taiwan", "all"] else "QQQ"
        try:
            data = collector.market_collector.fetch_yahoo_data(test_symbol, period="5d", interval="1d")
            if data is not None and len(data) > 0:
                logger.success(f"測試成功！獲取到 {len(data)} 筆 {test_symbol} 數據")
            else:
                logger.error("測試失敗！沒有獲取到數據")
                sys.exit(1)
        except Exception as e:
            logger.error(f"測試失敗: {e}")
            sys.exit(1)
    else:
        results = asyncio.run(collector.collect_all_data(args.market))
        
        if results['status'] == 'success':
            logger.success("✅ 數據收集任務完成！")
        elif results['status'] == 'partial_success':
            logger.warning("⚠️ 數據收集部分完成，存在一些錯誤")
            if args.debug and results.get('errors'):
                for error in results['errors'][:5]:  # 只顯示前5個錯誤
                    logger.warning(f"  - {error}")
        else:
            logger.error("❌ 數據收集任務失敗！")
            if results.get('error_message'):
                logger.error(f"錯誤訊息: {results['error_message']}")
            sys.exit(1)
        
        if 'summary' in results:
            summary = results['summary']
            logger.info(f"📊 處理統計: 市場檔案 {summary['total_market_files']} 個, 新聞 {summary['total_news']} 則")
            if summary['total_errors'] > 0:
                logger.warning(f"⚠️ 共 {summary['total_errors']} 個錯誤")
    
    logger.info("=== 數據收集智士結束 ===")

if __name__ == "__main__":
    main()
