#run_pipeline.py
import os
import sys
import json
import pandas as pd
from datetime import datetime
# 添加 scripts 目錄到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fetch_market_data import fetch_market_data
from quantity_strategy_0050 import run_backtest
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_podcast_script():
    # 檢查必要檔案是否存在
    required_files = ['data/daily_0050.csv', 'data/hourly_0050.csv']  # 更新為實際生成的檔案
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"缺少 {file}，無法生成播客腳本")
            return

    # 讀取市場數據
    try:
        daily_df = pd.read_csv('data/daily_0050.csv', parse_dates=['Date'], dtype={'Open': float, 'High': float, 'Low': float, 'Close': float, 'Adj Close': float, 'Volume': float, 'Symbol': str})
        hourly_0050_df = pd.read_csv('data/hourly_0050.csv', parse_dates=['Date'], dtype={'Open': float, 'High': float, 'Low': float, 'Close': float, 'Adj Close': float, 'Volume': float, 'Symbol': str})
    except Exception as e:
        logger.error(f"讀取市場數據失敗: {e}")
        return

    # 提取最新數據
    try:
        ts_0050 = daily_df.iloc[-1]
        ts_0050_prev = daily_df.iloc[-2]
        ts_0050_pct = ((ts_0050['Close'] - ts_0050_prev['Close']) / ts_0050_prev['Close']) * 100
    except:
        ts_0050 = {'Close': 'N/A', 'Volume': 'N/A'}
        ts_0050_pct = 'N/A'
        logger.warning("無法提取 0050.TW 數據")

    try:
        ts_0050_hourly = hourly_0050_df.iloc[-1]
    except:
        ts_0050_hourly = {'Close': 'N/A', 'Volume': 'N/A'}
        logger.warning("無法提取 0050.TW 小時線數據")

    # 假設外資期貨數據
    futures_net = "淨空 34,207 口，較前日減少 172 口（假設數據）"
    
    # 讀取量價策略輸出
    try:
        with open('data/daily_sim.json', 'r', encoding='utf-8') as f:
            daily_sim = json.load(f)
    except:
        daily_sim = {'signal': 'N/A', 'price': 'N/A', 'volume_rate': 'N/A', 'size_pct': 'N/A'}
        logger.warning("無法讀取 daily_sim.json")

    try:
        with open('data/backtest_report.json', 'r', encoding='utf-8') as f:
            backtest = json.load(f)
    except:
        backtest = {'metrics': {'sharpe_ratio': 'N/A', 'max_drawdown': 'N/A'}}
        logger.warning("無法讀取 backtest_report.json")

    try:
        with open('data/strategy_history.json', 'r', encoding='utf-8') as f:
            history = '\n'.join([f"{h['date']}: signal {h['strategy']['signal']}, sharpe {h['sharpe']}, mdd {h['mdd']}" for h in json.load(f)])
    except:
        history = "無歷史記錄"
        logger.warning("無法讀取 strategy_history.json")
    
    market_data = f"""
    - 0050.TW: 收盤 {ts_0050['Close'] if isinstance(ts_0050['Close'], (int, float)) else 'N/A'} 元，漲跌 {ts_0050_pct if isinstance(ts_0050_pct, (int, float)) else 'N/A'}%，成交量 {ts_0050['Volume'] if isinstance(ts_0050['Volume'], (int, float)) else 'N/A'} 股
    - 0050.TW 小時線: 最新價格 {ts_0050_hourly['Close'] if isinstance(ts_0050_hourly['Close'], (int, float)) else 'N/A'} 元，成交量 {ts_0050_hourly['Volume'] if isinstance(ts_0050_hourly['Close'], (int, float)) else 'N/A'} 股
    - 外資期貨未平倉水位: {futures_net}
    """
    
    # 讀取 prompt 並生成播報
    try:
        with open('prompt/tw.txt', 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        prompt = prompt.format(
            current_date=datetime.now().strftime('%Y-%m-%d'),
            market_data=market_data,
            SIG=daily_sim['signal'],
            PRICE=daily_sim['price'],
            VOLUME_RATE=daily_sim['volume_rate'],
            SIZE=daily_sim['size_pct'],
            OOS_SHARPE=backtest['metrics']['sharpe_ratio'],
            OOS_MDD=backtest['metrics']['max_drawdown'],
            LATEST_HISTORY=history
        )
        
        # 儲存播報
        os.makedirs('data', exist_ok=True)
        with open('data/podcast_script.txt', 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info("播客腳本已保存至 data/podcast_script.txt")
    except Exception as e:
        logger.error(f"生成播客腳本失敗: {e}")

def main():
    mode = os.environ.get('MODE', 'hourly')
    logger.info(f"以 {mode} 模式運行")
    
    # 抓取市場數據
    fetch_market_data()
    
    # 運行回測
    run_backtest()
    
    # 生成播報腳本
    generate_podcast_script()

if __name__ == '__main__':
    main()
