import argparse
import datetime
import os
import sys
from pathlib import Path
from loguru import logger
import pandas as pd
from dotenv import load_dotenv
# ta_bridge 整合 — TradingAgents 分析注入
sys.path.insert(0, str(Path(__file__).parent))
try:
    from ta_bridge import load_ta_cache
    _TA_BRIDGE = load_ta_cache()
    _TA_BRIDGE_AVAILABLE = _TA_BRIDGE is not None
    if _TA_BRIDGE_AVAILABLE:
        logger.info(f"✅ TA Bridge 已載入: {len(_TA_BRIDGE.get('market_analysis', {}))} 檔股票")
    else:
        logger.info("ℹ️ TA Bridge 無今日資料，使用原生流程")
except Exception as e:
    _TA_BRIDGE = None
    _TA_BRIDGE_AVAILABLE = False
    logger.info(f"ℹ️ TA Bridge 不可用: {e}")


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
        # ── TA Bridge：注入 TradingAgents 策略與 DCF 估值 ──
        if _TA_BRIDGE_AVAILABLE:
            ta_sr = _TA_BRIDGE.get("strategy_results", {}).get(symbol)
            if ta_sr:
                strategy_results[symbol]['ta_signal'] = ta_sr.get('ta_signal', 'HOLD')
                strategy_results[symbol]['ta_position'] = ta_sr.get('signals', {}).get('position', ta_sr.get('position', 'NEUTRAL'))
                strategy_results[symbol]['ta_confidence'] = ta_sr.get('ta_confidence', 0.5)
                if 'dcf' in ta_sr:
                    strategy_results[symbol]['dcf'] = ta_sr['dcf']
                logger.info(f"  ✅ {symbol} → TA: {ta_sr.get('ta_signal','?')} | {strategy_results[symbol].get('ta_position','?')}")
        market_analysis[symbol] = analyst.analyze_market(symbol)
        # ── TA Bridge 注入：TradingAgents 分析覆蓋 ──
        if _TA_BRIDGE_AVAILABLE:
            ta_ma = _TA_BRIDGE.get("market_analysis", {}).get(symbol)
            if ta_ma:
                # 用 TA 的分析覆蓋（TA 有更多的分析師觀點）
                original_ma = market_analysis[symbol]
                market_analysis[symbol] = ta_ma.copy()
                # 保留 podcast 原生的 MarketAnalyst 有用的欄位
                market_analysis[symbol]['original_report'] = str(original_ma.get('report',''))[:200]
                logger.info(f"  ✅ {symbol} → TA: trend={ta_ma.get('trend','?')} signal={ta_ma.get('ta_signal','?')}")

    
    # 步驟3: 生成文字稿
    # 偵錯用：印出目前在哪裡，以及目錄下有什麼
    print(f"目前工作目錄: {os.getcwd()}")
    print(f"根目錄下的檔案與資料夾: {os.listdir('.')}")
    if os.path.exists("docs"):
        print(f"doc 資料夾內的內容: {os.listdir('docs')}")

    # 正確的路徑寫法
    manual_script_path = os.path.join(os.getcwd(), "docs/script.txt")

    if os.path.exists(manual_script_path):
        print("成功找到手動腳本！")
    else:
        print(f"仍找不到檔案，路徑嘗試為: {manual_script_path}")
    
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
