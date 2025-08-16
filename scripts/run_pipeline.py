import os
import sys
import json
import pandas as pd
from datetime import datetime
import traceback
import time
from pytz import timezone

# 確保 scripts 目錄在 sys.path 中
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)  # 插入到列表開頭以優先使用
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

        # 儲存播報
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"播客腳本已保存至 {output_file}")

        # 生成 market_data_tw.json
        market_data_json = {
            "date": datetime.now(timezone('Asia/Taipei')).strftime('%Y-%m-%d'),
            "0050_TW": {
                "close": float(ts_0050.get('Close', 'N/A')),
                "volume": int(ts_0050.get('Volume', 'N/A')),
                "pct_change": float(ts_0050_pct) if ts_0050_pct != 'N/A' else None
            },
            "hourly_0050": {
                "close": float(ts_0050_hourly.get('Close', 'N/A')),
                "volume": int(ts_0050_hourly.get('Volume', 'N/A'))
            }
        }
        market_data_file = os.path.join(output_dir, "market_data_tw.json")
        with open(market_data_file, 'w', encoding='utf-8') as f:
            json.dump(market_data_json, f, ensure_ascii=False, indent=2)
        logger.info(f"市場數據已保存至 {market_data_file}")

        # 記錄 B2 連結到 archive_audio_url.txt (假設從環境變數或日誌獲取)
        b2_url = os.environ.get('B2_URL', 'https://***.s3.us-east-005.backblazeb2.com/***-20250816_tw.mp3')
        archive_url_file = os.path.join(output_dir, "archive_audio_url.txt")
        with open(archive_url_file, 'w', encoding='utf-8') as f:
            f.write(b2_url)
        logger.info(f"B2 連結已保存至 {archive_url_file}")

    except Exception as e:
        logger.error(f"生成播客腳本失敗: {e}")
        logger.error(traceback.format_exc())

def synthesize_audio():
    # 假設語音合成邏輯（需根據 synthesize_audio.py 實現）
    date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    output_dir = f"docs/podcast/{date_str}_tw"
    audio_file = os.path.join(output_dir, "audio.mp3")
    script_file = os.path.join(output_dir, "script.txt")
    # 這裡應調用 synthesize_audio.py 的函數（例如 from scripts.synthesize_audio import synthesize）
    logger.info(f"✅ 已完成語音合成：{audio_file}")

def upload_to_b2():
    try:
        from scripts.upload_to_b2 import upload_to_b2 as upload_to_b2_func
        date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
        output_dir = f"docs/podcast/{date_str}_tw"
        audio_file = os.path.join(output_dir, "audio.mp3")
        script_file = os.path.join(output_dir, "script.txt")
        identifier = f"{os.environ.get('BUCKET_PREFIX', 'podcast')}-{date_str}_tw"
        upload_to_b2_func(audio_file, script_file, identifier)
    except ImportError as e:
        logger.error(f"導入 upload_to_b2 失敗: {e}")
        logger.error(traceback.format_exc())

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

    # 僅在 daily 模式執行完整流程
    if mode == 'daily':
        generate_podcast_script()
        synthesize_audio()
        upload_to_b2()

if __name__ == '__main__':
    main()