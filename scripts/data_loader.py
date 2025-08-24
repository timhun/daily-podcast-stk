"""
數據載入工具
為策略模組提供統一的數據存取介面
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import json
from loguru import logger

from utils import config_manager, get_taiwan_time


class MarketDataLoader:
    """市場數據載入器"""
    
    def __init__(self):
        self.config = config_manager
        self.data_dir = Path("data/market")
        self.news_dir = Path("data/news")
    
    def get_available_symbols(self, data_type: str = "daily") -> List[str]:
        """
        獲取可用的股票代號列表
        
        Args:
            data_type: "daily" 或 "hourly"
        """
        if not self.data_dir.exists():
            return []
        
        symbols = []
        pattern = f"{data_type}_*.csv"
        
        for file in self.data_dir.glob(pattern):
            # 從檔案名提取股票代號
            symbol = file.stem.replace(f"{data_type}_", "")
            # 還原原始符號格式
            symbol = symbol.replace("_TW", ".TW").replace("_", "^") if "TW" in symbol else symbol
            symbols.append(symbol)
        
        return sorted(symbols)
    
    def load_symbol_data(
        self, 
        symbol: str, 
        data_type: str = "daily",
        days: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        載入指定股票的數據
        
        Args:
            symbol: 股票代號 (如 "^TWII", "2330.TW", "AAPL")
            data_type: "daily" 或 "hourly"
            days: 只載入最近幾天的數據，None 表示載入全部
        """
        # 轉換符號為檔案名格式
        clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')
        filename = self.data_dir / f"{data_type}_{clean_symbol}.csv"
        
        if not filename.exists():
            logger.warning(f"找不到 {symbol} 的 {data_type} 數據檔案: {filename}")
            return None
        
        try:
            data = pd.read_csv(filename)
            data['Datetime'] = pd.to_datetime(data['Datetime'])
            
            # 如果指定了天數限制
            if days is not None:
                cutoff_date = get_taiwan_time() - timedelta(days=days)
                data = data[data['Datetime'] >= cutoff_date]
            
            # 按時間排序
            data = data.sort_values('Datetime').reset_index(drop=True)
            
            logger.info(f"成功載入 {symbol} {data_type} 數據，共 {len(data)} 筆記錄")
            return data
            
        except Exception as e:
            logger.error(f"載入 {symbol} {data_type} 數據失敗: {str(e)}")
            return None
    
    def load_multiple_symbols(
        self, 
        symbols: List[str], 
        data_type: str = "daily",
        days: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        載入多個股票的數據
        
        Args:
            symbols: 股票代號列表
            data_type: "daily" 或 "hourly"
            days: 只載入最近幾天的數據
        """
        results = {}
        
        for symbol in symbols:
            data = self.load_symbol_data(symbol, data_type, days)
            if data is not None:
                results[symbol] = data
        
        logger.info(f"成功載入 {len(results)}/{len(symbols)} 支股票的 {data_type} 數據")
        return results
    
    def load_market_data(
        self, 
        market: str = "taiwan", 
        data_type: str = "daily",
        days: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        載入指定市場的所有股票數據
        
        Args:
            market: "taiwan", "us", "crypto"
            data_type: "daily" 或 "hourly"  
            days: 只載入最近幾天的數據
        """
        symbols = self.config.get(f"markets.{market}.symbols", [])
        if not symbols:
            logger.warning(f"找不到 {market} 市場的股票配置")
            return {}
        
        return self.load_multiple_symbols(symbols, data_type, days)
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        獲取股票的最新價格信息
        
        Args:
            symbols: 股票代號列表
            
        Returns:
            Dict[symbol, {"price": float, "change": float, "change_pct": float, "datetime": str}]
        """
        results = {}
        
        for symbol in symbols:
            data = self.load_symbol_data(symbol, "daily", days=5)
            if data is not None and len(data) >= 2:
                latest = data.iloc[-1]
                previous = data.iloc[-2]
                
                price = latest['Close']
                change = price - previous['Close']
                change_pct = (change / previous['Close']) * 100
                
                results[symbol] = {
                    'price': float(price),
                    'change': float(change),
                    'change_pct': float(change_pct),
                    'datetime': latest['Datetime'].isoformat(),
                    'volume': float(latest['Volume']) if pd.notna(latest['Volume']) else 0
                }
        
        return results
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        計算常用技術指標
        
        Args:
            data: 價格數據 DataFrame
            
        Returns:
            包含技術指標的 DataFrame
        """
        if data is None or len(data) < 20:
            return data
        
        df = data.copy()
        
        try:
            # 移動平均線
            df['SMA_5'] = df['Close'].rolling(window=5).mean()
            df['SMA_10'] = df['Close'].rolling(window=10).mean()
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean() if len(df) >= 50 else None
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 布林通道
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
            
            # MACD
            if len(df) >= 26:
                exp1 = df['Close'].ewm(span=12).mean()
                exp2 = df['Close'].ewm(span=26).mean()
                df['MACD'] = exp1 - exp2
                df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
                df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # 成交量移動平均
            df['Volume_SMA'] = df['Volume'].rolling(window=10).mean()
            
            logger.debug(f"已計算技術指標，數據長度: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"計算技術指標失敗: {str(e)}")
            return data
    
    def get_data_summary(self) -> Dict:
        """獲取數據摘要統計"""
        summary = {
            'total_files': 0,
            'daily_files': 0,
            'hourly_files': 0,
            'markets': {},
            'last_updated': None
        }
        
        if not self.data_dir.exists():
            return summary
        
        # 統計檔案數量
        daily_files = list(self.data_dir.glob("daily_*.csv"))
        hourly_files = list(self.data_dir.glob("hourly_*.csv"))
        
        summary['daily_files'] = len(daily_files)
        summary['hourly_files'] = len(hourly_files)
        summary['total_files'] = len(daily_files) + len(hourly_files)
        
        # 按市場分類統計
        for market in ['taiwan', 'us', 'crypto']:
            symbols = self.config.get(f"markets.{market}.symbols", [])
            available_count = 0
            
            for symbol in symbols:
                clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')
                daily_file = self.data_dir / f"daily_{clean_symbol}.csv"
                if daily_file.exists():
                    available_count += 1
            
            summary['markets'][market] = {
                'configured': len(symbols),
                'available': available_count,
                'coverage': f"{available_count/len(symbols)*100:.1f}%" if symbols else "0%"
            }
        
        # 找最新更新時間
        all_files = daily_files + hourly_files
        if all_files:
            latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
            summary['last_updated'] = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
        
        return summary


class NewsDataLoader:
    """新聞數據載入器"""
    
    def __init__(self):
        self.news_dir = Path("data/news")
    
    def get_available_dates(self) -> List[str]:
        """獲取可用的新聞日期列表"""
        if not self.news_dir.exists():
            return []
        
        dates = []
        for date_dir in self.news_dir.iterdir():
            if date_dir.is_dir():
                dates.append(date_dir.name)
        
        return sorted(dates, reverse=True)
    
    def load_news(
        self, 
        market: str = "taiwan", 
        days: int = 7
    ) -> List[Dict]:
        """
        載入指定市場的新聞
        
        Args:
            market: "taiwan" 或 "us"
            days: 載入最近幾天的新聞
        """
        all_news = []
        
        # 獲取最近幾天的日期
        end_date = get_taiwan_time()
        dates_to_load = []
        
        for i in range(days):
            date_str = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            dates_to_load.append(date_str)
        
        # 載入新聞
        for date_str in dates_to_load:
            date_dir = self.news_dir / date_str
            news_file = date_dir / f"{market}_news.json"
            
            if news_file.exists():
                try:
                    with open(news_file, 'r', encoding='utf-8') as f:
                        news_data = json.load(f)
                        all_news.extend(news_data)
                except Exception as e:
                    logger.error(f"載入新聞失敗 {news_file}: {str(e)}")
        
        logger.info(f"載入 {market} 市場最近 {days} 天新聞，共 {len(all_news)} 則")
        return all_news
    
    def get_news_summary(self, days: int = 30) -> Dict:
        """獲取新聞摘要統計"""
        summary = {
            'total_days': 0,
            'total_news': 0,
            'by_market': {},
            'recent_dates': []
        }
        
        available_dates = self.get_available_dates()
        summary['recent_dates'] = available_dates[:10]  # 最近10天
        
        # 統計最近指定天數的新聞
        end_date = get_taiwan_time()
        target_dates = [
            (end_date - timedelta(days=i)).strftime("%Y-%m-%d") 
            for i in range(days)
        ]
        
        for market in ['taiwan', 'us']:
            market_total = 0
            market_days = 0
            
            for date_str in target_dates:
                if date_str in available_dates:
                    date_dir = self.news_dir / date_str
                    news_file = date_dir / f"{market}_news.json"
                    
                    if news_file.exists():
                        try:
                            with open(news_file, 'r', encoding='utf-8') as f:
                                news_data = json.load(f)
                                market_total += len(news_data)
                                market_days += 1
                        except:
                            pass
            
            summary['by_market'][market] = {
                'total_news': market_total,
                'available_days': market_days,
                'avg_per_day': market_total / market_days if market_days > 0 else 0
            }
            summary['total_news'] += market_total
        
        summary['total_days'] = len([d for d in target_dates if d in available_dates])
        return summary


# 便利函數
def load_taiwan_stocks(data_type: str = "daily", days: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """快速載入台股數據"""
    loader = MarketDataLoader()
    return loader.load_market_data("taiwan", data_type, days)

def load_us_stocks(data_type: str = "daily", days: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """快速載入美股數據"""
    loader = MarketDataLoader()
    return loader.load_market_data("us", data_type, days)

def load_crypto_data(data_type: str = "daily", days: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """快速載入加密貨幣數據"""
    loader = MarketDataLoader()
    return loader.load_market_data("crypto", data_type, days)

def get_stock_data(symbol: str, data_type: str = "daily", days: Optional[int] = None, with_indicators: bool = False) -> Optional[pd.DataFrame]:
    """
    快速獲取單一股票數據
    
    Args:
        symbol: 股票代號
        data_type: "daily" 或 "hourly"
        days: 載入最近幾天的數據
        with_indicators: 是否計算技術指標
    """
    loader = MarketDataLoader()
    data = loader.load_symbol_data(symbol, data_type, days)
    
    if data is not None and with_indicators:
        data = loader.calculate_technical_indicators(data)
    
    return data

def get_latest_prices(symbols: Optional[List[str]] = None, market: str = "taiwan") -> Dict[str, Dict]:
    """
    快速獲取最新價格
    
    Args:
        symbols: 股票代號列表，None 表示使用市場預設配置
        market: 當 symbols 為 None 時使用的市場
    """
    loader = MarketDataLoader()
    
    if symbols is None:
        symbols = config_manager.get(f"markets.{market}.symbols", [])
    
    return loader.get_latest_prices(symbols)

def get_market_news(market: str = "taiwan", days: int = 7) -> List[Dict]:
    """快速獲取市場新聞"""
    loader = NewsDataLoader()
    return loader.load_news(market, days)


# 測試功能
if __name__ == "__main__":
    # 測試數據載入功能
    print("=== 數據載入工具測試 ===")
    
    # 測試市場數據載入
    market_loader = MarketDataLoader()
    summary = market_loader.get_data_summary()
    print(f"數據摘要: {summary}")
    
    # 測試載入台股數據
    taiwan_data = load_taiwan_stocks("daily", days=30)
    print(f"載入台股數據: {len(taiwan_data)} 支股票")
    
    # 測試新聞載入
    news_loader = NewsDataLoader()
    news_summary = news_loader.get_news_summary()
    print(f"新聞摘要: {news_summary}")
    
    print("測試完成！")
