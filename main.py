import argparse
import datetime
import os
from dotenv import load_dotenv
from data_collector import collect_data
from content_creator import generate_script
from voice_producer import generate_audio
from cloud_manager import upload_episode
from podcast_distributor import generate_rss, notify_slack
from strategy_mastermind import StrategyEngine  # 新增
import pytz

load_dotenv()

def main(mode):
    TW_TZ = pytz.timezone("Asia/Taipei")
    today = datetime.datetime.now(TW_TZ).strftime("%Y%m%d")
    #today = datetime.date.today().strftime('%Y%m%d')
    print(f"Starting {mode.upper()} podcast production for {today}...")

    # 步驟1: 收集數據
    market_data = collect_data(mode)

    # 步驟2: 執行策略分析
    strategy_engine = StrategyEngine()
    strategy_results = {}
    market_analysis = {}  # 新增市場分析結果
    analyst = MarketAnalyst()  # 新增 MarketAnalyst 實例
    for symbol in market_data['market']:
        strategy_results[symbol] = strategy_engine.run_strategy_tournament(symbol, market_data['market'][symbol])
        market_analysis[symbol] = analyst.analyze_market(symbol)  # 新增市場分析

    # 步驟3: 生成文字稿
    script = generate_script(market_data, mode, strategy_results, market_analysis)  # 傳入市場分析結果
    script_path = f"episodes/{today}_{mode}/script.txt"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    # 步驟4: 生成音頻
    audio_path = f"episodes/{today}_{mode}/audio.mp3"
    generate_audio(script_path, audio_path)

    # 步驟5: 上傳到 B2
    files = {'script': script_path, 'audio': audio_path}
    uploaded_urls = upload_episode(today, mode, files)
    audio_url = uploaded_urls['audio']

    # 步驟6: 生成 RSS + Slack 通知
    generate_rss(today, mode, script, audio_url)
    notify_slack(today, mode, audio_url)

    print("Podcast production completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['us', 'tw'])
    args = parser.parse_args()
    main(args.mode)
