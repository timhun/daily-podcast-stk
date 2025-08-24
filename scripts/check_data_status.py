#!/usr/bin/env python3
"""
GitHub Actions 專用數據狀態檢查腳本
檢查數據收集的結果並生成摘要報告
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加 scripts 目錄到 Python 路徑
sys.path.append(str(Path(__file__).parent))

from utils import get_taiwan_time, config_manager
from loguru import logger

def check_market_data_status():
    """檢查市場數據狀態"""
    data_dir = Path("data/market")
    
    if not data_dir.exists():
        logger.error("data/market 目錄不存在")
        return {}
    
    status = {
        'daily_files': [],
        'hourly_files': [],
        'total_files': 0,
        'file_sizes': {},
        'last_updated': {},
        'markets': {
            'taiwan': {'daily': 0, 'hourly': 0, 'symbols': []},
            'us': {'daily': 0, 'hourly': 0, 'symbols': []},
            'crypto': {'daily': 0, 'hourly': 0, 'symbols': []}
        }
    }
    
    # 掃描所有 CSV 檔案
    for csv_file in data_dir.glob("*.csv"):
        file_size = csv_file.stat().st_size
        last_modified = datetime.fromtimestamp(csv_file.stat().st_mtime)
        
        status['file_sizes'][csv_file.name] = file_size
        status['last_updated'][csv_file.name] = last_modified.isoformat()
        status['total_files'] += 1
        
        if csv_file.name.startswith('daily_'):
            status['daily_files'].append(csv_file.name)
            symbol = csv_file.name.replace('daily_', '').replace('.csv', '')
            
            # 判斷市場類型
            if '_TW' in symbol or symbol.startswith('TWII'):
                status['markets']['taiwan']['daily'] += 1
                status['markets']['taiwan']['symbols'].append(symbol)
            elif any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'USD']):
                status['markets']['crypto']['daily'] += 1
                status['markets']['crypto']['symbols'].append(symbol)
            else:
                status['markets']['us']['daily'] += 1
                status['markets']['us']['symbols'].append(symbol)
        
        elif csv_file.name.startswith('hourly_'):
            status['hourly_files'].append(csv_file.name)
            symbol = csv_file.name.replace('hourly_', '').replace('.csv', '')
            
            # 判斷市場類型
            if '_TW' in symbol or symbol.startswith('TWII'):
                status['markets']['taiwan']['hourly'] += 1
            elif any(crypto in symbol.upper() for crypto in ['BTC', 'ETH', 'USD']):
                status['markets']['crypto']['hourly'] += 1
            else:
                status['markets']['us']['hourly'] += 1
    
    return status

def check_news_data_status():
    """檢查新聞數據狀態"""
    news_dir = Path("data/news")
    
    if not news_dir.exists():
        logger.error("data/news 目錄不存在")
        return {}
    
    status = {
        'total_dates': 0,
        'total_news_files': 0,
        'dates': [],
        'news_counts': {},
        'latest_news': {}
    }
    
    # 掃描日期目錄
    for date_dir in news_dir.iterdir():
        if date_dir.is_dir():
            status['dates'].append(date_dir.name)
            status['total_dates'] += 1
            
            # 檢查該日期的新聞檔案
            for news_file in date_dir.glob("*.json"):
                status['total_news_files'] += 1
                
                try:
                    with open(news_file, 'r', encoding='utf-8') as f:
                        news_data = json.load(f)
                        count = len(news_data)
                        
                    status['news_counts'][f"{date_dir.name}/{news_file.name}"] = count
                    
                    # 記錄最新的新聞
                    if date_dir.name == max(status['dates']) if status['dates'] else None:
                        status['latest_news'][news_file.name] = count
                        
                except Exception as e:
                    logger.error(f"讀取新聞檔案失敗 {news_file}: {str(e)}")
    
    status['dates'].sort(reverse=True)
    return status

def validate_data_quality():
    """驗證數據品質"""
    data_dir = Path("data/market")
    issues = []
    
    if not data_dir.exists():
        return ["data/market 目錄不存在"]
    
    # 檢查各市場的配置股票是否都有數據
    for market in ['taiwan', 'us', 'crypto']:
        symbols = config_manager.get(f"markets.{market}.symbols", [])
        missing_daily = []
        missing_hourly = []
        
        for symbol in symbols:
            clean_symbol = symbol.replace('^', '').replace('.', '_').replace('=', '_').replace('-', '_')
            
            daily_file = data_dir / f"daily_{clean_symbol}.csv"
            hourly_file = data_dir / f"hourly_{clean_symbol}.csv"
            
            if not daily_file.exists():
                missing_daily.append(symbol)
            else:
                # 檢查檔案是否為空
                try:
                    df = pd.read_csv(daily_file)
                    if len(df) < 10:
                        issues.append(f"{symbol} 日線數據過少: {len(df)} 筆")
                except Exception as e:
                    issues.append(f"{symbol} 日線數據讀取失敗: {str(e)}")
            
            if not hourly_file.exists():
                missing_hourly.append(symbol)
        
        if missing_daily:
            issues.append(f"{market} 市場缺少日線數據: {missing_daily}")
        if missing_hourly:
            issues.append(f"{market} 市場缺少小時線數據: {missing_hourly}")
    
    return issues

def generate_summary_report():
    """生成摘要報告"""
    logger.info("=== GitHub Actions 數據狀態報告 ===")
    
    # 檢查市場數據
    market_status = check_market_data_status()
    logger.info(f"市場數據檔案總數: {market_status.get('total_files', 0)}")
    logger.info(f"日線數據檔案: {len(market_status.get('daily_files', []))}")
    logger.info(f"小時線數據檔案: {len(market_status.get('hourly_files', []))}")
    
    for market, data in market_status.get('markets', {}).items():
        logger.info(f"{market} 市場: 日線 {data['daily']} 檔, 小時線 {data['hourly']} 檔")
    
    # 檢查新聞數據
    news_status = check_news_data_status()
    logger.info(f"新聞數據日期總數: {news_status.get('total_dates', 0)}")
    logger.info(f"新聞檔案總數: {news_status.get('total_news_files', 0)}")
    
    if news_status.get('latest_news'):
        logger.info("最新新聞統計:")
        for file, count in news_status['latest_news'].items():
            logger.info(f"  {file}: {count} 則新聞")
    
    # 檢查數據品質
    issues = validate_data_quality()
    if issues:
        logger.warning("發現數據品質問題:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.success("數據品質檢查通過")
    
    # 生成 GitHub Actions 輸出
    summary = {
        'timestamp': get_taiwan_time().isoformat(),
        'market_data': market_status,
        'news_data': news_status,
        'data_quality_issues': issues,
        'status': 'success' if not issues else 'warning'
    }
    
    # 儲存詳細報告
    report_file = Path("data/collection_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"詳細報告已儲存到: {report_file}")
    
    return summary

def main():
    """主函數"""
    try:
        logger.info("開始數據狀態檢查...")
        report = generate_summary_report()
        
        if report['status'] == 'success':
            logger.success("✅ 數據狀態檢查完成，一切正常")
            return 0
        else:
            logger.warning("⚠️ 數據狀態檢查完成，發現一些問題")
            return 1
            
    except Exception as e:
        logger.error(f"數據狀態檢查失敗: {str(e)}")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
