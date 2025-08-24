#!/usr/bin/env python3
"""
配置測試腳本
用於診斷配置檔案載入問題
"""

import sys
from pathlib import Path

# 添加 scripts 目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent))

from utils import config_manager
from loguru import logger

def test_config():
    """測試配置載入"""
    logger.info("=== 配置測試開始 ===")
    
    # 檢查當前工作目錄
    cwd = Path.cwd()
    logger.info(f"當前工作目錄: {cwd}")
    
    # 檢查項目結構
    logger.info("項目結構檢查:")
    for path in ["config", "scripts", "data"]:
        path_obj = Path(path)
        exists = path_obj.exists()
        logger.info(f"  {path}: {'存在' if exists else '不存在'}")
        if exists and path_obj.is_dir():
            for item in path_obj.iterdir():
                logger.info(f"    - {item.name}")
    
    # 測試配置讀取
    logger.info("\n配置讀取測試:")
    
    # 測試系統配置
    log_level = config_manager.get("system.log_level", "未找到")
    logger.info(f"系統日誌等級: {log_level}")
    
    # 測試台股配置
    taiwan_symbols = config_manager.get("markets.taiwan.symbols", [])
    logger.info(f"台股股票數量: {len(taiwan_symbols)}")
    if taiwan_symbols:
        logger.info(f"台股股票列表: {taiwan_symbols}")
    else:
        logger.error("台股股票列表為空！")
    
    # 測試美股配置
    us_symbols = config_manager.get("markets.us.symbols", [])
    logger.info(f"美股股票數量: {len(us_symbols)}")
    
    # 測試新聞來源
    taiwan_news = config_manager.get("markets.taiwan.news_sources", [])
    logger.info(f"台股新聞源數量: {len(taiwan_news)}")
    
    logger.info("=== 配置測試結束 ===")
    
    return len(taiwan_symbols) > 0

if __name__ == "__main__":
    success = test_config()
    if not success:
        logger.error("配置測試失敗！")
        sys.exit(1)
    else:
        logger.success("配置測試成功！")
