#!/usr/bin/env python3
"""
yfinance 數據結構調試腳本
用於診斷 yfinance 返回的數據格式
"""

import sys
from pathlib import Path
import yfinance as yf
import pandas as pd

# 添加 scripts 目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent))

from utils import get_taiwan_time
from loguru import logger

def debug_yfinance_data():
    """調試 yfinance 數據結構"""
    
    test_symbols = [
        "^TWII",      # 台股加權指數
        "2330.TW",    # 台積電
        "0050.TW",    # 台灣50
        "AAPL",       # 蘋果
        "^GSPC",      # S&P 500
        "BTC-USD"     # 比特幣
    ]
    
    for symbol in test_symbols:
        logger.info(f"\n=== 測試 {symbol} ===")
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="5d", interval="1d")
            
            logger.info(f"數據形狀: {data.shape}")
            logger.info(f"索引名稱: {data.index.name}")
            logger.info(f"索引類型: {type(data.index)}")
            logger.info(f"欄位: {list(data.columns)}")
            
            if not data.empty:
                logger.info(f"數據範例:")
                print(data.head(2))
                print(f"索引前2個值: {data.index[:2].tolist()}")
                
                # 測試 reset_index
                data_reset = data.copy()
                data_reset.reset_index(inplace=True)
                logger.info(f"reset_index 後的欄位: {list(data_reset.columns)}")
                
                # 檢查第一行數據
                if len(data_reset) > 0:
                    first_row = data_reset.iloc[0]
                    logger.info(f"第一行數據類型:")
                    for col in data_reset.columns:
                        logger.info(f"  {col}: {type(first_row[col])} = {first_row[col]}")
            else:
                logger.warning(f"{symbol} 沒有數據")
                
        except Exception as e:
            logger.error(f"{symbol} 發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()

def test_data_processing():
    """測試數據處理流程"""
    
    symbol = "^TWII"
    logger.info(f"\n=== 完整流程測試: {symbol} ===")
    
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="5d", interval="1d")
        
        if data.empty:
            logger.error(f"{symbol} 沒有獲取到數據")
            return None
        
        logger.info("原始數據:")
        print(data.head(2))
        
        # 添加股票代號和更新時間欄位
        data['Symbol'] = symbol
        data['Updated'] = get_taiwan_time().isoformat()
        
        # 重設索引
        logger.info("\n執行 reset_index...")
        data.reset_index(inplace=True)
        logger.info(f"reset_index 後的欄位: {list(data.columns)}")
        
        # 檢查並重命名時間欄位
        if 'Date' in data.columns:
            logger.info("發現 'Date' 欄位，重命名為 'Datetime'")
            data.rename(columns={'Date': 'Datetime'}, inplace=True)
        elif 'Datetime' not in data.columns:
            logger.error("找不到時間欄位")
            return None
        
        # 檢查必要欄位
        required_columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            logger.error(f"缺少必要欄位: {missing_columns}")
            return None
        
        logger.info("最終數據:")
        print(data[['Datetime', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume']].head(2))
        
        return data
        
    except Exception as e:
        logger.error(f"數據處理失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    logger.info("=== yfinance 數據結構調試 ===")
    
    # 檢查 yfinance 版本
    logger.info(f"yfinance 版本: {yf.__version__}")
    
    # 調試數據結構
    debug_yfinance_data()
    
    # 測試完整處理流程
    test_data_processing()
    
    logger.info("\n=== 調試完成 ===")

if __name__ == "__main__":
    main()
