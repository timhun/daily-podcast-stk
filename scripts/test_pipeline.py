#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

# 設定日誌
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment():
    """測試環境設定"""
    logger.info("=== 環境測試 ===")
    
    # 測試 Python 版本
    logger.info(f"Python 版本: {sys.version}")
    
    # 測試必要模組
    required_modules = ['yfinance', 'pandas', 'backtrader', 'numpy']
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✓ {module} 已安裝")
        except ImportError:
            logger.error(f"✗ {module} 未安裝")
    
    # 測試目錄結構
    required_dirs = ['data', 'prompt']
    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists():
            logger.info(f"✓ 目錄 {dir_name} 存在")
        else:
            logger.warning(f"! 目錄 {dir_name} 不存在，將創建")
            path.mkdir(exist_ok=True)

def test_data_fetch():
    """測試數據抓取"""
    logger.info("=== 數據抓取測試 ===")
    
    try:
        from fetch_market_data import fetch_market_data
        fetch_market_data()
        
        # 檢查生成的檔案
        expected_files = ['data/daily_0050.csv', 'data/hourly_0050.csv']
        for file_path in expected_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                logger.info(f"✓ {file_path} 存在，大小: {size} bytes")
            else:
                logger.error(f"✗ {file_path} 不存在")
                
    except Exception as e:
        logger.error(f"數據抓取測試失敗: {e}")

def test_backtest():
    """測試回測功能"""
    logger.info("=== 回測測試 ===")
    
    try:
        from quantity_strategy_0050 import run_backtest
        run_backtest()
        
        # 檢查回測結果檔案
        result_files = ['data/daily_sim.json', 'data/backtest_report.json']
        for file_path in result_files:
            if os.path.exists(file_path):
                logger.info(f"✓ {file_path} 生成成功")
            else:
                logger.error(f"✗ {file_path} 未生成")
                
    except Exception as e:
        logger.error(f"回測測試失敗: {e}")

def test_pipeline():
    """測試完整流程"""
    logger.info("=== 完整流程測試 ===")
    
    try:
        from run_pipeline import main
        main()
        
        # 檢查最終輸出
        if os.path.exists('data/podcast_script.txt'):
            with open('data/podcast_script.txt', 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"✓ 播客腳本生成成功，長度: {len(content)} 字元")
        else:
            logger.error("✗ 播客腳本未生成")
            
    except Exception as e:
        logger.error(f"完整流程測試失敗: {e}")

if __name__ == '__main__':
    test_environment()
    test_data_fetch()
    test_backtest()
    test_pipeline()
    logger.info("=== 測試完成 ===")
