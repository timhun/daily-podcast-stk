import os
import sys
import json
import pandas as pd
from datetime import datetime
import traceback
import time
from pytz import timezone
import asyncio

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

def generate_podcast_script(date_str=None):
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
                elif f"{col} '0050.TW'" in df.columns:
                    df[col] = pd.to_numeric(df[f"{col} '0050.TW'"], errors='coerce')
                elif f"{col} '0050.TW'" in df.columns.values:
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
            current_date=datetime.now(timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
            market_data=market_data,
            SIG=daily_sim.get('signal', 'N/A'),
            PRICE=daily_sim.get('price', 'N/A'),
            VOLUME_RATE=daily_sim.get('volume_rate', 'N/A'),
            SIZE=daily_sim.get('size_pct', 'N/A'),
            OOS_SHARPE=backtest['metrics'].get('sharpe_ratio', 'N/A'),
            OOS_MDD=backtest['metrics'].get('max_drawdown', 'N/A'),
            LATEST_HISTORY=history
        )

        # 根據日期生成目錄和檔案
        date_str = date_str or datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
        output_dir = f"docs/podcast/{date_str}_tw"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "script.txt")

        # 儲存播報，覆蓋現有檔案
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"播客腳本已保存至 {output_file}")
    except Exception as e:
        logger.error(f"生成播客腳本失敗: {e}")
        logger.error(traceback.format_exc())

def synthesize_audio():
    # 導入 synthesize_audio 模組
    from synthesize_audio import synthesize as synthesize_audio_func
    date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_tw"
    script_path = os.path.join(base_dir, "script.txt")
    if os.path.exists(script_path):
        os.environ['PODCAST_MODE'] = 'tw'
        asyncio.run(synthesize_audio_func())
    else:
        logger.warning(f"⚠️ 找不到逐字稿 {script_path}，跳過語音合成")

def upload_to_b2():
    # 導入 upload_to_b2 模組
    import upload_to_b2
    date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_tw"
    audio_path = os.path.join(base_dir, "audio.mp3")
    script_path = os.path.join(base_dir, "script.txt")
    if os.path.exists(audio_path) and os.path.exists(script_path):
        os.environ['PODCAST_MODE'] = 'tw'
        upload_to_b2.upload_to_b2()
    else:
        logger.warning(f"⚠️ 找不到 {audio_path} 或 {script_path}，跳過 B2 上傳")

def generate_rss():
    # 導入 generate_rss 模組
    import generate_rss
    date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_tw"
    audio_path = os.path.join(base_dir, "audio.mp3")
    archive_url_file = os.path.join(base_dir, "archive_audio_url.txt")
    if os.path.exists(audio_path) and os.path.exists(archive_url_file):
        os.environ['PODCAST_MODE'] = 'tw'
        generate_rss.generate_rss()
    else:
        logger.warning(f"⚠️ 找不到 {audio_path} 或 {archive_url_file}，跳過 RSS 生成")

def main():
    # 獲取當前時間 (CST)
    current_time = datetime.now().astimezone(timezone('Asia/Taipei'))
    mode = os.environ.get('MODE', 'auto')
    is_manual = os.environ.get('MANUAL_TRIGGER', '0') == '1' or mode == 'manual'
    logger.info(f"以 {mode} 模式運行，當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S CST')}, 手動觸發: {is_manual}")

    if mode not in ['hourly', 'daily', 'weekly', 'auto', 'manual']:
        logger.error(f"無效的 MODE: {mode}, 使用預設 auto")
        mode = 'auto'

    # 根據模式和時間觸發任務
    if mode == 'auto':
        # 每天 16:00 CST 生成文字稿，其餘時間每小時回測
        if current_time.hour == 16 and 0 <= current_time.minute < 5:
            mode = 'daily'
            os.environ['INTERVAL'] = '1d'
            os.environ['DAYS'] = '90'
        else:
            mode = 'hourly'
            os.environ['INTERVAL'] = '1h'
            os.environ['DAYS'] = '7'
    elif is_manual:
        # 手動觸發時強制生成當日文字稿
        mode = 'daily'
        os.environ['INTERVAL'] = '1d'
        os.environ['DAYS'] = '90'

    # 根據模式調整數據範圍
    if mode == 'hourly':
        os.environ['INTERVAL'] = '1h'
        os.environ['DAYS'] = '7'
    elif mode == 'daily':
        os.environ['INTERVAL'] = '1d'
        os.environ['DAYS'] = '90'
    elif mode == 'weekly':
        os.environ['INTERVAL'] = '1wk'
        os.environ['DAYS'] = '365'

    # 抓取市場數據
    fetch_market_data()

    # 運行回測
    run_backtest()

    # 僅在 daily 模式生成播客腳本並合成語音、上傳至 B2 並生成 RSS
    if mode == 'daily':
        generate_podcast_script()
        synthesize_audio()
        upload_to_b2()
        generate_rss()

if __name__ == '__main__':
    main()
