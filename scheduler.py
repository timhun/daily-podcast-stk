#!/usr/bin/env python3
"""
統一排程器 - 整合現有回測 + 新增 Prompt 每日優化

整合：
- 現有：strategy_mastermind.py 的每日回測 (14:00)
- 新增：run_daily_optimization.py 的每日優化 (06:30)
"""

import os
import sys
import schedule
import time
import threading
from datetime import datetime
from loguru import logger

# 設定路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 載入設定
import json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 設定日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

# ─────────────────────────────────────────────
# 任務 1：現有每日回測 (14:00)
# ─────────────────────────────────────────────

def run_daily_backtest():
    """每日策略回測 - 來自 strategy_mastermind.py"""
    try:
        from strategy_mastermind import StrategyEngine
        engine = StrategyEngine()
        engine.daily_backtest(mode='tw')
        engine.daily_backtest(mode='us')
        logger.info("✅ 每日回測完成")
    except Exception as e:
        logger.error(f"❌ 每日回測失敗: {e}")

# ─────────────────────────────────────────────
# 任務 2：新增每日 Prompt 優化 (06:30)
# ─────────────────────────────────────────────

def run_daily_prompt_optimization():
    """每日 Prompt 自動優化"""
    try:
        # 設定環境變數
        os.environ['PYTHONPATH'] = os.getcwd()
        
        # 執行優化
        from run_daily_optimization import run_full_optimization
        result = run_full_optimization()
        logger.info(f"✅ 每日 Prompt 優化完成: {result.get('optimization', {}).get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ 每日 Prompt 優化失敗: {e}")

# ─────────────────────────────────────────────
# 任務 3：週末深度優化 (週六 10:00)
# ─────────────────────────────────────────────

def run_weekend_deep_optimization():
    """週末深度優化：執行 A/B 測試、多版本對比"""
    try:
        os.environ['PYTHONPATH'] = os.getcwd()
        from auto_prompt_optimizer_v2 import PromptOptimizerV2
        from prompts.registry import initialize_default_version
        
        initialize_default_version()
        optimizer = PromptOptimizerV2()
        
        # 執行 A/B 測試當前版本 vs 最佳版本
        current = optimizer.registry.get_current_version()
        best = optimizer.registry.get_best_version()
        
        if current != best:
            logger.info(f"🧪 週末 A/B 測試: v{current} vs v{best}")
            optimizer.start_ab_test(current, best)
            # 這裡可以加入更完整的 A/B 測試邏輯
            optimizer.end_ab_test(best)
            logger.info("✅ 週末 A/B 測試完成")
        else:
            logger.info("ℹ️ 當前版本即最佳版本，跳過 A/B 測試")
            
    except Exception as e:
        logger.error(f"❌ 週末深度優化失敗: {e}")

# ─────────────────────────────────────────────
# 排程設定
# ─────────────────────────────────────────────

def setup_schedules():
    """設定所有排程"""
    
    # 平日每日回測 (週一至週五 14:00)
    schedule.every().monday.at("14:00").do(run_daily_backtest)
    schedule.every().tuesday.at("14:00").do(run_daily_backtest)
    schedule.every().wednesday.at("14:00").do(run_daily_backtest)
    schedule.every().thursday.at("14:00").do(run_daily_backtest)
    schedule.every().friday.at("14:00").do(run_daily_backtest)
    
    # 每日 Prompt 優化 (週一至週五 06:30) - 在開盤前
    schedule.every().monday.at("06:30").do(run_daily_prompt_optimization)
    schedule.every().tuesday.at("06:30").do(run_daily_prompt_optimization)
    schedule.every().wednesday.at("06:30").do(run_daily_prompt_optimization)
    schedule.every().thursday.at("06:30").do(run_daily_prompt_optimization)
    schedule.every().friday.at("06:30").do(run_daily_prompt_optimization)
    
    # 週末深度優化 (週六 10:00)
    schedule.every().saturday.at("10:00").do(run_weekend_deep_optimization)
    
    logger.info("📅 排程設定完成:")
    logger.info("  - 平日 14:00: 策略回測 (TW + US)")
    logger.info("  - 平日 06:30: Prompt 每日優化")
    logger.info("  - 週六 10:00: 週末深度優化 (A/B 測試)")

# ─────────────────────────────────────────────
# 主程式
# ─────────────────────────────────────────────

def run_scheduler():
    """執行排程器主迴圈"""
    setup_schedules()
    logger.info("🚀 排程器啟動，等待任務...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次

def run_once(task_name: str):
    """手動執行單一任務 (測試用)"""
    tasks = {
        "backtest": run_daily_backtest,
        "prompt_opt": run_daily_prompt_optimization,
        "weekend": run_weekend_deep_optimization,
    }
    if task_name in tasks:
        logger.info(f"手動執行: {task_name}")
        tasks[task_name]()
    else:
        logger.error(f"未知任務: {task_name}")
        logger.info(f"可用任務: {list(tasks.keys())}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="統一排程器")
    parser.add_argument("--run", action="store_true", help="啟動排程器主迴圈")
    parser.add_argument("--once", choices=["backtest", "prompt_opt", "weekend"], help="手動執行單一任務")
    parser.add_argument("--list", action="store_true", help="列出所有排程任務")
    args = parser.parse_args()
    
    if args.list:
        setup_schedules()
        for job in schedule.jobs:
            print(f"  {job.next_run} | {job.job_func.__name__}")
    elif args.once:
        run_once(args.once)
    elif args.run:
        run_scheduler()
    else:
        parser.print_help()
