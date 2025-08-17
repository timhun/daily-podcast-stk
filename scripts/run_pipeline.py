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

def generate_podcast_script(date_str=None, mode='tw'):
    # 根據模式設定符號和提示檔案
    symbol = '0050.TW' if mode == 'tw' else 'QQQ'
    prompt_file = 'prompt/tw.txt' if mode == 'tw' else 'prompt/us.txt'

    # 檢查必要檔案是否存在
    required_files = [f'data/daily_{symbol}.csv', f'data/hourly_{symbol}.csv']
    podcast_symbols = ['^TWII', 'BTC-USD', 'DJI', 'GC=F', 'GSPC', 'IXIC', 'SPY']
    required_files.extend([f'data/daily_{s}.csv' for s in podcast_symbols])
    for file in required_files:
        if not os.path.exists(file):
            logger.error(f"缺少 {file}，無法生成播客腳本")
            return

    # 讀取市場數據
    try:
        daily_df = pd.read_csv(f'data/daily_{symbol}.csv')
        hourly_df = pd.read_csv(f'data/hourly_{symbol}.csv')

        # 讀取 podcast 相關數據
        podcast_data = {}
        for s in podcast_symbols:
            df = pd.read_csv(f'data/daily_{s}.csv')
            if len(df) >= 2:
                ts = df.iloc[-1]
                ts_prev = df.iloc[-2]
                # 確保 Close 為數值型態
                ts['Close'] = pd.to_numeric(ts['Close'], errors='coerce')
                ts_prev['Close'] = pd.to_numeric(ts_prev['Close'], errors='coerce')
                pct = ((ts['Close'] - ts_prev['Close']) / ts_prev['Close'] * 100) if not pd.isna(ts_prev['Close']) and ts_prev['Close'] != 0 else 'N/A'
                podcast_data[s] = {'Close': ts['Close'], 'pct': pct}
            else:
                podcast_data[s] = {'Close': 'N/A', 'pct': 'N/A'}

        # 轉換日期欄位，處理缺失情況
        if 'Date' not in daily_df.columns:
            logger.warning(f"{symbol} daily_df 中缺少 Date 欄位，從索引生成")
            daily_df['Date'] = pd.to_datetime(daily_df.index)
        else:
            daily_df['Date'] = pd.to_datetime(daily_df['Date'])
        
        if 'Date' not in hourly_df.columns:
            logger.warning(f"{symbol} hourly_df 中缺少 Date 欄位，從索引生成")
            hourly_df['Date'] = pd.to_datetime(hourly_df.index)
        else:
            hourly_df['Date'] = pd.to_datetime(hourly_df['Date'])

        # 確保數值欄位為正確型態
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in numeric_columns:
            for df in [daily_df, hourly_df]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

        # 確保數據不為空
        if daily_df.empty or hourly_df.empty:
            logger.error(f"{symbol} 市場數據為空，無法生成播客腳本")
            return

    except Exception as e:
        logger.error(f"讀取 {symbol} 市場數據失敗: {e}")
        logger.error(traceback.format_exc())
        return

    # 提取最新數據
    try:
        if len(daily_df) >= 2:
            ts = daily_df.iloc[-1]
            ts_prev = daily_df.iloc[-2]
            # 確保 Close 為數值型態
            ts['Close'] = pd.to_numeric(ts['Close'], errors='coerce')
            ts_prev['Close'] = pd.to_numeric(ts_prev['Close'], errors='coerce')
            ts_pct = ((ts['Close'] - ts_prev['Close']) / ts_prev['Close'] * 100) if not pd.isna(ts_prev['Close']) and ts_prev['Close'] != 0 else 'N/A'
        else:
            ts = daily_df.iloc[-1] if len(daily_df) > 0 else pd.Series({'Close': 'N/A', 'Volume': 'N/A'})
            ts_pct = 'N/A'
    except Exception as e:
        logger.warning(f"無法提取 {symbol} 數據: {e}")
        ts = pd.Series({'Close': 'N/A', 'Volume': 'N/A'})
        ts_pct = 'N/A'

    try:
        ts_hourly = hourly_df.iloc[-1]
    except Exception as e:
        logger.warning(f"無法提取 {symbol} 小時線數據: {e}")
        ts_hourly = pd.Series({'Close': 'N/A', 'Volume': 'N/A'})

    # 格式化市場數據，移除外資期貨假設數據
    market_data = f"""
- {symbol}: 收盤 {format_number(ts.get('Close'))} 元，漲跌 {format_number(ts_pct)}%，成交量 {format_number(ts.get('Volume'), 0)} 股
- {symbol} 小時線: 最新價格 {format_number(ts_hourly.get('Close'))} 元，成交量 {format_number(ts_hourly.get('Volume'), 0)} 股
"""
    # 添加 podcast 相關數據
    for s in podcast_symbols:
        data = podcast_data[s]
        market_data += f"\n- {s}: 收盤 {format_number(data['Close'])}, 漲跌 {format_number(data['pct'])}%"

    # 讀取量價策略輸出
    sim_file = f'data/daily_sim_{symbol}.json'
    try:
        if os.path.exists(sim_file):
            with open(sim_file, 'r', encoding='utf-8') as f:
                daily_sim = json.load(f)
            daily_sim = daily_sim[-1] if isinstance(daily_sim, list) else daily_sim
        else:
            daily_sim = {'signal': '無訊號', 'price': 'N/A', 'volume_rate': 'N/A', 'size_pct': 'N/A'}
    except Exception as e:
        logger.warning(f"無法讀取 {sim_file}: {e}")
        daily_sim = {'signal': '無訊號', 'price': 'N/A', 'volume_rate': 'N/A', 'size_pct': 'N/A'}

    try:
        with open(f'data/backtest_report_{symbol}.json', 'r', encoding='utf-8') as f:
            backtest = json.load(f)
    except Exception as e:
        logger.warning(f"無法讀取 backtest_report_{symbol}.json: {e}")
        backtest = {'metrics': {'sharpe_ratio': 'N/A', 'max_drawdown': 'N/A'}}

    try:
        with open(f'data/strategy_history_{symbol}.json', 'r', encoding='utf-8') as f:
            history = '\n'.join([f"{h['date']}: signal {h['strategy'].get('signal', 'N/A')}, sharpe {h.get('sharpe', 'N/A')}, mdd {h.get('mdd', 'N/A')}" for h in json.load(f)])
    except Exception as e:
        logger.warning(f"無法讀取 strategy_history_{symbol}.json: {e}")
        history = "無歷史記錄"

    # 讀取 prompt 並生成播報
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
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

        # 根據日期和模式生成目錄和檔案
        date_str = date_str or datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
        output_dir = f"docs/podcast/{date_str}_{mode}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "script.txt")

        # 儲存播報，覆蓋現有檔案
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"播客腳本已保存至 {output_file}")
    except Exception as e:
        logger.error(f"生成 {mode} 播客腳本失敗: {e}")
        logger.error(traceback.format_exc())

def synthesize_audio(date_str=None, mode='tw'):
    # 嘗試導入 synthesize_audio 模組，處理缺失情況
    try:
        from synthesize_audio import synthesize as synthesize_audio_func
    except ImportError as e:
        logger.error(f"無法導入 synthesize_audio 模組: {e}，請確保已安裝 edge-tts")
        return
    date_str = date_str or datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_{mode}"
    script_path = os.path.join(base_dir, "script.txt")
    if os.path.exists(script_path):
        os.environ['PODCAST_MODE'] = mode
        asyncio.run(synthesize_audio_func())
    else:
        logger.warning(f"⚠️ 找不到 {mode} 逐字稿 {script_path}，跳過語音合成")

def upload_to_b2(date_str=None, mode='tw'):
    # 嘗試導入 upload_to_b2 模組，處理缺失情況
    try:
        import upload_to_b2
    except ImportError as e:
        logger.error(f"無法導入 upload_to_b2 模組: {e}，請檢查依賴")
        return
    date_str = date_str or datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_{mode}"
    audio_path = os.path.join(base_dir, "audio.mp3")
    script_path = os.path.join(base_dir, "script.txt")
    if os.path.exists(audio_path) and os.path.exists(script_path):
        os.environ['PODCAST_MODE'] = mode
        upload_to_b2.upload_to_b2()
    else:
        logger.warning(f"⚠️ 找不到 {mode} {audio_path} 或 {script_path}，跳過 B2 上傳")

def generate_rss(date_str=None, mode='tw'):
    # 嘗試導入 generate_rss 模組，處理缺失情況
    try:
        import generate_rss
    except ImportError as e:
        logger.error(f"無法導入 generate_rss 模組: {e}，請檢查依賴")
        return
    date_str = date_str or datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
    base_dir = f"docs/podcast/{date_str}_{mode}"
    audio_path = os.path.join(base_dir, "audio.mp3")
    archive_url_file = os.path.join(base_dir, "archive_audio_url.txt")
    if os.path.exists(audio_path) and os.path.exists(archive_url_file):
        os.environ['PODCAST_MODE'] = mode
        generate_rss.generate_rss()
    else:
        logger.warning(f"⚠️ 找不到 {mode} {audio_path} 或 {archive_url_file}，跳過 RSS 生成")

def main():
    # 獲取當前時間 (CST)
    current_time = datetime.now().astimezone(timezone('Asia/Taipei'))
    mode = os.environ.get('MODE', 'auto')
    is_manual = os.environ.get('MANUAL_TRIGGER', '0') == '1' or mode == 'manual'
    podcast_mode = os.environ.get('PODCAST_MODE', 'auto')  # 從環境變數獲取
    if is_manual and 'podcast_mode' in os.environ:
        podcast_mode = os.environ.get('podcast_mode', 'auto')  # 覆蓋為手動輸入
    logger.info(f"以 {mode} 模式運行，當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S CST')}, 手動觸發: {is_manual}, PODCAST_MODE: {podcast_mode}")

    if mode not in ['hourly', 'daily', 'weekly', 'auto', 'manual']:
        logger.error(f"無效的 MODE: {mode}, 使用預設 auto")
        mode = 'auto'

    # 根據模式和時間觸發任務
    if mode == 'auto':
        # 每天 06:00 CST 生成美股文字稿，16:00 CST 生成台股文字稿，其餘時間每小時回測
        if current_time.hour == 6 and 0 <= current_time.minute < 5:
            mode = 'daily'
            os.environ['INTERVAL'] = '1d'
            os.environ['DAYS'] = '90'
            os.environ['PODCAST_MODE'] = 'us'
            generate_podcast_script(mode='us')
            synthesize_audio(mode='us')
            upload_to_b2(mode='us')
            generate_rss(mode='us')
        elif current_time.hour == 16 and 0 <= current_time.minute < 5:
            mode = 'daily'
            os.environ['INTERVAL'] = '1d'
            os.environ['DAYS'] = '90'
            os.environ['PODCAST_MODE'] = 'tw'
            generate_podcast_script(mode='tw')
            synthesize_audio(mode='tw')
            upload_to_b2(mode='tw')
            generate_rss(mode='tw')
        else:
            mode = 'hourly'
            os.environ['INTERVAL'] = '1h'
            os.environ['DAYS'] = '7'
    elif is_manual:
        # 手動觸發時根據 podcast_mode 生成指定模式
        mode = 'daily'
        os.environ['INTERVAL'] = '1d'
        os.environ['DAYS'] = '90'
        date_str = datetime.now(timezone('Asia/Taipei')).strftime('%Y%m%d')
        fetch_market_data()  # 確保手動模式下總是抓取數據
        if podcast_mode in ['tw', 'us']:
            os.environ['PODCAST_MODE'] = podcast_mode
            generate_podcast_script(date_str, podcast_mode)
            synthesize_audio(date_str, podcast_mode)
            upload_to_b2(date_str, podcast_mode)
            generate_rss(date_str, podcast_mode)
        else:
            for m in ['tw', 'us']:
                os.environ['PODCAST_MODE'] = m
                generate_podcast_script(date_str, m)
                synthesize_audio(date_str, m)
                upload_to_b2(date_str, m)
                generate_rss(date_str, m)

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

    # 僅在自動回測時執行 fetch_market_data（避免與手動重複）
    if not is_manual and (mode in ['hourly', 'weekly'] and mode != 'auto'):
        fetch_market_data()

    # 運行回測（根據符號調整）
    run_backtest()

if __name__ == '__main__':
    main()
