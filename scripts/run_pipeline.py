import os
import sys
import json
import pandas as pd
from datetime import datetime
import traceback

# 添加 scripts 目錄到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fetch_market_data import fetch_market_data
from quantity_strategy_0050 import run_backtest
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_number(value, decimal_places=2):
    """安全的數字格式化函數"""
    if isinstance(value, (int, float)) and not pd.isna(value):
        return f"{value:.{decimal_places}f}"
    return 'N/A'

def generate_podcast_script():
    # 檢查必要檔案是否存在
    required_files = ['data/daily_0050.csv', 'data/hourly_0050.csv']
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"缺少 {file}，無法生成播客腳本")
            return

    # 讀取市場數據
    try:
        daily_df = pd.read_csv('data/daily_0050.csv')
        hourly_0050_df = pd.read_csv('data/hourly_0050.csv')

        # 轉換日期欄位，處理缺失情況
        if 'Date' not in daily_df.columns:
            logger.warning("daily_df 中缺少 Date 欄位，從索引生成")
            daily_df['Date'] = pd.to_datetime(daily_df.index)
        else:
            daily_df['Date'] = pd.to_datetime(daily_df['Date'])
        
        if 'Date' not in hourly_0050_df.columns:
            logger.warning("hourly_0050_df 中缺少 Date 欄位，從索引生成")
            hourly_0050_df['Date'] = pd.to_datetime(hourly_0050_df.index)
        else:
            hourly_0050_df['Date'] = pd.to_datetime(hourly_0050_df['Date'])

        # 確保數值欄位為正確型態，處理可能的 '0050.TW' 後綴
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in numeric_columns:
            for df in [daily_df, hourly_0050_df]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif f"{col} '0050.TW'" in df.columns:  # 處理可能的後綴
                    df[col] = pd.to_numeric(df[f"{col} '0050.TW'"], errors='coerce')
                elif f"{col} '0050.TW'" in df.columns.values:  # 更靈活的匹配
                    df[col] = pd.to_numeric(df[df.columns[df.columns.str.contains(col)][0]], errors='coerce')

        # 確保數據不為空
        if daily_df.empty or hourly_0050_df.empty:
            logger.error("市場數據為空，無法生成播客腳本")
            return

    except Exception as e:
        logger.error(f"讀取市場數據失敗: {e}")
        logger.error(traceback.format_exc())
        return

    # 提取最新數據
    try:
        if len(daily_df) >= 2:
            ts_0050 = daily_df.iloc[-1]
            ts_0050_prev = daily_df.iloc[-2]
            # 確保使用 Series 索引
            ts_0050_pct = ((ts_0050['Close'] - ts_0050_prev['Close']) / ts_0050_prev['Close'] * 100) if not pd.isna(ts_0050_prev['Close']) else 'N/A'
        else:
            ts_0050 = daily_df.iloc[-1] if len(daily_df) > 0 else pd.Series({'Close': 'N/A', 'Volume': 'N/A'})
            ts_0050_pct = 'N/A'
    except Exception as e:
        logger.warning(f"無法提取 0050.TW 數據: {e}")
        ts_0050 = pd.Series({'Close': 'N/A', 'Volume': 'N/A'})
        ts_0050_pct = 'N/A'

    try:
        ts_0050_hourly = hourly_0050_df.iloc[-1]
    except Exception as e:
        logger.warning(f"無法提取 0050.TW 小時線數據: {e}")
        ts_0050_hourly = pd.Series({'Close': 'N/A', 'Volume': 'N/A'})

    # 假設外資期貨數據
    futures_net = "淨空 34,207 口，較前日減少 172 口（假設數據）"

    # 讀取量價策略輸出
    try:
        if os.path.exists('data/daily_sim.json'):
            with open('data/daily_sim.json', 'r', encoding='utf-8') as f:
                daily_sim = json.load(f)
            # 確保使用最新訊號
            daily_sim = daily_sim[-1] if isinstance(daily_sim, list) else daily_sim
        else:
            daily_sim = {'signal': '無訊號', 'price': 'N/A', 'volume_rate': 'N/A', 'size_pct': 'N/A'}
    except Exception as e:
        logger.warning(f"無法讀取 daily_sim.json: {e}")
        daily_sim = {'signal': '無訊號', 'price': 'N/A', 'volume_rate': 'N/A', 'size_pct': 'N/A'}

    try:
        with open('data/backtest_report.json', 'r', encoding='utf-8') as f:
            backtest = json.load(f)
    except Exception as e:
        logger.warning(f"無法讀取 backtest_report.json: {e}")
        backtest = {'metrics': {'sharpe_ratio': 'N/A', 'max_drawdown': 'N/A'}}

    try:
        with open('data/strategy_history.json', 'r', encoding='utf-8') as f:
            history = '\n'.join([f"{h['date']}: signal {h['strategy'].get('signal', 'N/A')}, sharpe {h.get('sharpe', 'N/A')}, mdd {h.get('mdd', 'N/A')}" for h in json.load(f)])
    except Exception as e:
        logger.warning(f"無法讀取 strategy_history.json: {e}")
        history = "無歷史記錄"

    # 格式化市場數據
    market_data = f"""
    - 0050.TW: 收盤 {format_number(ts_0050.get('Close'))} 元，漲跌 {format_number(ts_0050_pct)}%，成交量 {format_number(ts_0050.get('Volume'), 0)} 股
    - 0050.TW 小時線: 最新價格 {format_number(ts_0050_hourly.get('Close'))} 元，成交量 {format_number(ts_0050_hourly.get('Volume'), 0)} 股
    - 外資期貨未平倉水位: {futures_net}
    """

    # 讀取 prompt 並生成播報
    try:
        with open('prompt/tw.txt', 'r', encoding='utf-8') as f:
            prompt = f.read()

        prompt = prompt.format(
            current_date=datetime.now().strftime('%Y-%m-%d'),
            market_data=market_data,
            SIG=daily_sim.get('signal', 'N/A'),
            PRICE=daily_sim.get('price', 'N/A'),
            VOLUME_RATE=daily_sim.get('volume_rate', 'N/A'),
            SIZE=daily_sim.get('size_pct', 'N/A'),
            OOS_SHARPE=backtest['metrics'].get('sharpe_ratio', 'N/A'),
            OOS_MDD=backtest['metrics'].get('max_drawdown', 'N/A'),
            LATEST_HISTORY=history
        )

        # 儲存播報
        os.makedirs('data', exist_ok=True)
        with open('data/podcast_script.txt', 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info("播客腳本已保存至 data/podcast_script.txt")
    except Exception as e:
        logger.error(f"生成播客腳本失敗: {e}")
        logger.error(traceback.format_exc())

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