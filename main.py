import argparse
import datetime
import os
from dotenv import load_dotenv
import pandas as pd
from data_collector import collect_data
from content_creator import generate_script
from voice_producer import generate_audio
from cloud_manager import upload_episode
from podcast_distributor import generate_rss, notify_slack
from strategy_mastermind import StrategyEngine
from market_analyst import MarketAnalyst
from loguru import logger
import json
import pytz

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 設置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

load_dotenv()

def main(mode):
    TW_TZ = pytz.timezone("Asia/Taipei")
    today = datetime.datetime.now(TW_TZ).strftime("%Y%m%d")
    logger.info(f"開始生成 {mode.upper()} 版 podcast，日期 {today}...")

    # 步驟 1：收集新聞和情緒數據
    market_data = collect_data(mode)  # 僅用於新聞和情緒數據

    # 步驟 2：從 CSV 載入市場數據並執行策略分析
    strategy_engine = StrategyEngine()
    analyst = MarketAnalyst(config)
    strategy_results = {}
    market_analysis = {}
   for symbol in market_data['market']:
        # Load the full DataFrame from CSV for historical data
        file_path = f"{config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_')}.csv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        else:
            df = pd.DataFrame()
            print(f"Warning: No data for {symbol}, using empty DataFrame")

        try:
            strategy_results[symbol] = strategy_engine.run_strategy_tournament(symbol, df)
            market_analysis[symbol] = analyst.analyze_market(symbol)
            logger.info(f"{symbol} 策略和市場分析完成")
        except Exception as e:
            logger.error(f"{symbol} 策略執行失敗：{str(e)}")
            strategy_results[symbol] = {
                'symbol': symbol,
                'analysis_date': datetime.datetime.now(TW_TZ).strftime('%Y-%m-%d'),
                'index_symbol': '^TWII' if symbol == '0050.TW' else '^IXIC',
                'winning_strategy': {'name': 'none', 'confidence': 0.0, 'expected_return': 0.0, 'max_drawdown': 0.0, 'sharpe_ratio': 0.0},
                'signals': {'position': 'NEUTRAL', 'entry_price': 0.0, 'target_price': 0.0, 'stop_loss': 0.0, 'position_size': 0.0},
                'dynamic_params': {},
                'strategy_version': '2.0'
            }
            market_analysis[symbol] = {'trend': 'Unknown', 'rsi': 0.0}

    # 儲存策略結果
    output_dir = f"{config['data_paths']['strategy']}/{datetime.datetime.now(TW_TZ).strftime('%Y-%m-%d')}"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/strategy_results.json", 'w', encoding='utf-8') as f:
        json.dump(strategy_results, f, ensure_ascii=False, indent=2)
    logger.info(f"策略結果儲存至：{output_dir}/strategy_results.json")

    # 步驟 3：生成文字稿
    podcast_dir = f"{config['data_paths']['podcast']}/{today}_{mode}"
    script_filename = f"{config['b2_podcast_prefix']}-{today}_{mode}.txt"
    script_path = f"{podcast_dir}/{script_filename}"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    script = generate_script(market_data, mode, strategy_results, market_analysis)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿儲存至：{script_path}")

    # 步驟 4：生成音頻
    audio_filename = f"{config['b2_podcast_prefix']}-{today}_{mode}.mp3"
    audio_path = f"{podcast_dir}/{audio_filename}"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    generate_audio(script_path, audio_path)
    logger.info(f"音頻儲存至：{audio_path}")

    # 步驟 5：上傳至 B2
    files = {'script': script_path, 'audio': audio_path}
    uploaded_urls = upload_episode(today, mode, files)
    audio_url = uploaded_urls['audio']
    logger.info(f"已上傳至 B2：{audio_url}")

    # 步驟 6：生成 RSS 和 Slack 通知
    generate_rss(today, mode, script, audio_url)
    notify_slack(today, mode, audio_url)
    logger.info("Podcast 生成完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['us', 'tw'])
    args = parser.parse_args()
    main(args.mode)


