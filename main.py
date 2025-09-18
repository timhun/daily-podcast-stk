import argparse
import datetime
import os
import pandas as pd
from dotenv import load_dotenv
from data_collector import collect_data
from content_creator import generate_script
from voice_producer import generate_audio
from cloud_manager import upload_episode
from podcast_distributor import generate_rss, notify_slack_enhanced
from strategy_mastermind import StrategyEngine
from market_analyst import MarketAnalyst
import pytz
import json
from loguru import logger

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

load_dotenv()

def is_weekday():
    """Check if today is a weekday (Monday to Friday) in Taipei timezone."""
    TW_TZ = pytz.timezone("Asia/Taipei")
    today = datetime.datetime.now(TW_TZ)
    return today.weekday() < 5  # Monday (0) to Friday (4) are weekdays

def main(mode):
    TW_TZ = pytz.timezone("Asia/Taipei")
    today = datetime.datetime.now(TW_TZ).strftime("%Y%m%d")
    print(f"開始生成 {mode.upper()} 版 podcast，日期 {today}...")

    # 步驟1: 收集數據
    market_data = collect_data(mode)

    # 步驟2: 執行策略分析
    strategy_engine = StrategyEngine()
    strategy_results = {}
    market_analysis = {}
    analyst = MarketAnalyst(config)
    for symbol in market_data['market']:
        file_path = f"{config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'], utc=True)
                df.set_index('date', inplace=True)
                if df.empty or 'close' not in df.columns:
                    logger.warning(f"{symbol} CSV 為空或缺少 'close' 欄位")
                    df = pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
            else:
                logger.warning(f"找不到 {symbol} 的 CSV 檔案：{file_path}")
                df = pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
        except Exception as e:
            logger.error(f"載入 {symbol} CSV 失敗：{str(e)}")
            df = pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
    
        strategy_results[symbol] = strategy_engine.run_strategy_tournament(symbol, df)
        market_analysis[symbol] = analyst.analyze_market(symbol)
    
        # Step 2.5: Optimize strategies (background)
        is_weekday_result = is_weekday()  # Call the function to check if today is a weekday
        if is_weekday_result:
            strategy_engine.optimize_all_strategies(strategy_results, mode, iterations=1, background=True)
        else:
            strategy_engine.optimize_all_strategies(strategy_results, mode, iterations=3, extended_data=True, background=True)
            
    # 步驟3: 生成文字稿
    podcast_dir = f"{config['data_paths']['podcast']}/{today}_{mode}"
    script_filename = f"{config['b2_podcast_prefix']}-{today}_{mode}.txt"
    script_path = f"{podcast_dir}/{script_filename}"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    script = generate_script(market_data, mode, strategy_results, market_analysis)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    # 步驟4: 生成音頻
    audio_filename = f"{config['b2_podcast_prefix']}-{today}_{mode}.mp3"
    audio_path = f"{podcast_dir}/{audio_filename}"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(script_path, audio_path)

    # 步驟5: 上傳到 B2
    files = {'script': script_path, 'audio': audio_path}
    uploaded_urls = upload_episode(today, mode, files)
    audio_url = uploaded_urls['audio']

    # 步驟6: 生成 RSS + Slack 通知
    generate_rss(today, mode, script, audio_url)
    notify_slack_enhanced(strategy_results, mode)

    print("Podcast 製作完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['us', 'tw'])
    args = parser.parse_args()
    main(args.mode)