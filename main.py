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
from strategies.god_system_strategy import GodSystemStrategy
from strategies.bigline_strategy import BigLineStrategy
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

def build_placeholder_df(symbol):
    """Create placeholder OHLCV data when market CSV is missing or invalid."""
    periods = 252
    dates = pd.date_range(start='2025-01-01', periods=periods, tz='UTC')
    base_open = 22987.92
    close_series = [base_open + i * 10 for i in range(periods)]
    return pd.DataFrame({
        'date': dates,
        'symbol': [symbol] * periods,
        'open': [base_open] * periods,
        'high': [base_open + 12] * periods,
        'low': [base_open - 80] * periods,
        'close': close_series,
        'change': [0.0] + [0.01] * (periods - 1),
        'volume': [5_000_000] * periods
    })

def main(mode):
    TW_TZ = pytz.timezone("Asia/Taipei")
    today = datetime.datetime.now(TW_TZ).strftime("%Y%m%d")
    print(f"開始生成 {mode.upper()} 版 podcast，日期 {today}...")

    # 步驟1: 收集數據
    market_data = collect_data(mode)

    # 步驟2: 執行策略分析
    strategies_map = {
        'god_system': GodSystemStrategy(config),
        'bigline': BigLineStrategy(config)
    }
    strategy_results = {}
    market_analysis = {}
    analyst = MarketAnalyst(config)
    symbol_sentiments = market_data.get('sentiment', {}).get('symbols', {})
    overall_sentiment = market_data.get('sentiment', {}).get('overall_score', 0.0)

    for symbol in market_data['market']:
        file_path = f"{config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
        try:
            if os.path.exists(file_path):
                df_raw = pd.read_csv(file_path)
                if df_raw.empty or 'close' not in df_raw.columns:
                    logger.warning(f"{symbol} CSV 為空或缺少 'close' 欄位")
                    df_raw = build_placeholder_df(symbol)
            else:
                logger.warning(f"找不到 {symbol} 的 CSV 檔案：{file_path}")
                df_raw = build_placeholder_df(symbol)
        except Exception as e:
            logger.error(f"載入 {symbol} CSV 失敗：{str(e)}")
            df_raw = build_placeholder_df(symbol)

        df_raw['date'] = pd.to_datetime(df_raw['date'], utc=True, errors='coerce')
        df_raw = df_raw.dropna(subset=['date']).sort_values('date')
        sentiment_score = symbol_sentiments.get(symbol, {}).get('sentiment_score', overall_sentiment if overall_sentiment is not None else 0.0)
        if sentiment_score is None:
            sentiment_score = 0.0
        df_raw['sentiment_score'] = sentiment_score

        df_bigline = df_raw.copy()
        df_god = df_raw.copy()
        df_god.set_index('date', inplace=True, drop=False)

        per_strategy_results = {}
        for strategy_name, strategy in strategies_map.items():
            if strategy_name == 'god_system':
                result = strategy.backtest(symbol, df_god.copy(), timeframe='daily')
            else:
                result = strategy.backtest(symbol, df_bigline.copy(), timeframe='daily')
            per_strategy_results[strategy_name] = result
            logger.info(
                f"{symbol} {strategy_name} 策略: Sharpe={result.get('sharpe_ratio', 0):.2f}, "
                f"MaxDrawdown={result.get('max_drawdown', 0):.2f}, "
                f"ExpectedReturn={result.get('expected_return', 0):.2f}, "
                f"Signal={result.get('signals', {}).get('position', 'NEUTRAL')}"
            )

        best_name, best_result = max(
            per_strategy_results.items(),
            key=lambda item: item[1].get('expected_return', float('-inf'))
        )

        strategy_results[symbol] = {
            'strategy': best_name,
            'expected_return': best_result.get('expected_return', 0),
            'max_drawdown': best_result.get('max_drawdown', 0),
            'sharpe_ratio': best_result.get('sharpe_ratio', 0),
            'signals': best_result.get('signals', {}),
            'best': {'name': best_name, **best_result},
            'strategies': per_strategy_results
        }
        market_analysis[symbol] = analyst.analyze_market(symbol)
    
    # 步驟3: 生成文字稿
    # 1. 定義路徑
    # 注意：如果 doc 是在專案根目錄，路徑寫 'doc/script.txt' 即可
    manual_script_path = "doc/script.txt" 
    
    podcast_dir = f"{config['data_paths']['podcast']}/{today}_{mode}"
    script_filename = f"{config['b2_podcast_prefix']}-{today}_{mode}.txt"
    script_path = f"{podcast_dir}/{script_filename}"
    
    # 確保輸出目錄存在
    os.makedirs(os.path.dirname(script_path), exist_ok=True)

    # 2. 核心判斷邏輯
    if os.path.exists(manual_script_path):
        print(f"--- 偵測到手動稿件: {manual_script_path} ---")
        with open(manual_script_path, 'r', encoding='utf-8') as f:
            script = f.read()
    else:
        print(f"--- 未發現手動稿件，執行自動生成流程 ---")
        script = generate_script(market_data, mode, strategy_results, market_analysis)

    # 3. 統一寫入到當天有日期的正式路徑 (確保後續 TTS 或上傳流程能找到檔案)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    print(f"文字稿已準備就緒，存檔於: {script_path}")

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
    generate_rss(today, mode, script, audio_url, strategy_results)
    # notify_slack_enhanced(strategy_results, mode)

    print("Podcast 製作完成！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['us', 'tw'])
    args = parser.parse_args()
    main(args.mode)
