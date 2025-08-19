# scripts/script_editor.py
import pandas as pd
import json
import os
from datetime import datetime
import logging
import requests
from feedparser import parse
import argparse

# 設定日誌
logging.basicConfig(filename='logs/script_editor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 Grok API
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')  # 假設的 API 端點

# CSV 對應表
SYMBOL_FILE_MAP = {
    '^TWII': 'daily_^TWII.csv',
    '0050.TW': 'daily_0050.TW.csv',
    'QQQ': 'hourly_QQQ.csv',
    'SPY': 'hourly_SPY.csv',
    'BTC-USD': 'hourly_BTC.csv',
    'GC=F': 'hourly_GC.csv',
    '^DJI': 'hourly_^DJI.csv',
    '^IXIC': 'hourly_^IXIC.csv',
    '^GSPC': 'hourly_^GSPC.csv'
}

def load_config(mode=None):
    """載入配置檔案 config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        rss_url = config.get('rss_url', 'https://tw.stock.yahoo.com/rss?category=news')
        news_keywords = config.get('news_keywords', ['經濟', '半導體'])
        symbol_map = {'tw': '0050.TW', 'us': 'QQQ'}
        symbol = symbol_map.get(mode, '0050.TW')
        return rss_url, news_keywords, symbol
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def fetch_rss_news(rss_url, keywords, max_news=3):
    """從 RSS 抓取最新新聞，篩選標題"""
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        feed = parse(response.text)
        news = []
        for entry in feed.entries:
            title = entry.title
            if any(keyword in title for keyword in keywords):
                news.append({
                    'title': title,
                    'link': entry.link,
                    'published': entry.get('published', '')
                })
            if len(news) >= max_news:
                break
        news.sort(key=lambda x: x['published'], reverse=True)
        logger.info(f"RSS 抓取結果: {len(news)} 則新聞")
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

def load_market_data(symbol):
    """從 data 目錄讀取最新收盤價與漲跌幅"""
    file_name = SYMBOL_FILE_MAP.get(symbol, f'daily_{symbol}.csv')
    file_path = os.path.join('data', file_name)
    if not os.path.exists(file_path):
        logger.warning(f"找不到市場數據檔案: {file_path}")
        return {'close': None, 'pct_change': 0.0}
    try:
        df = pd.read_csv(file_path)
        latest = df.iloc[-1]
        close = float(latest.get('close', latest.get('Close', 0)))
        pct_change = float(latest.get('pct_change', latest.get('PctChange', 0)))
        return {'close': close, 'pct_change': pct_change}
    except Exception as e:
        logger.error(f"讀取市場數據失敗: {e}")
        return {'close': None, 'pct_change': 0.0}

def load_analysis(symbol):
    """載入策略管理師與市場分析師的輸出"""
    strategy_path = os.path.join('data', f'strategy_best_{symbol}.json')
    market_path = os.path.join('data', f'market_analysis_{symbol}.json')
    strategy = {}
    market = {}
    try:
        if os.path.exists(strategy_path):
            with open(strategy_path, 'r', encoding='utf-8') as f:
                strategy = json.load(f)
        if os.path.exists(market_path):
            with open(market_path, 'r', encoding='utf-8') as f:
                market = json.load(f)
    except Exception as e:
        logger.error(f"讀取分析資料失敗: {e}")
    return strategy, market

def generate_script(mode, debug_data=False):
    """生成 podcast 文字稿"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    rss_url, keywords, main_symbol = load_config(mode)
    news = fetch_rss_news(rss_url, keywords)
    strategy, market = load_analysis(main_symbol)

    # 主要標的收盤
    main_data = load_market_data(main_symbol)

    # 其他市場指數
    if mode == 'us':
        indices_symbols = ['^DJI', '^IXIC', '^GSPC', 'QQQ', 'SPY', 'BTC-USD', 'GC=F']
        market_name = "美股"
    else:
        indices_symbols = ['^TWII', '0050.TW']
        market_name = "台股"
    market_indices = {sym: load_market_data(sym) for sym in indices_symbols}

    # 組文字稿
    script = f"大家好，這裡是《幫幫忙說{market_name}》\n日期：{date_str}\n\n"

    # 市場概況
    for sym, data in market_indices.items():
        script += f"{sym} 收盤 {data['close']}, 漲跌 {data['pct_change']}%\n"
    script += "\n"

    # 焦點標的分析
    script += "焦點標的分析：\n"
    if strategy:
        script += f"策略分析師建議使用策略：{strategy.get('best_strategy', 'N/A')}，參數：{strategy.get('params', {})}\n"
    if market:
        script += f"市場分析師建議：{market.get('recommendation', '持倉')}, 倉位 {market.get('position_size', 0.0)}\n"
        script += f"風險提醒：{market.get('risk_note', '')}\n"
    script += "\n"

    # 新聞摘要
    script += "新聞摘要:\n"
    for n in news:
        script += f"- {n['title']} ({n['published']}) {n['link']}\n"
    script += "\n"

    # AI 投資機會
    script += "AI 投資機會:\n- 人工智慧雲端服務\n- AI 芯片與硬體加速\n- AI 智能交易平台\n\n"

    # 結尾
    script += "記住 Kostolany 說過：『股市短期波動，長期才是致勝。』"

    # Debug 輸出
    if debug_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join('logs', f'script_editor_debug_{timestamp}.json')
        os.makedirs('logs', exist_ok=True)
        debug_content = {
            'mode': mode,
            'main_symbol': main_symbol,
            'strategy': strategy,
            'market': market,
            'market_indices': market_indices,
            'rss_news': news
        }
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_content, f, ensure_ascii=False, indent=2)
        logger.info(f"Debug 資料已保存至 {debug_file}")

    return script

def improve_with_grok(script):
    """使用 Grok API 優化文字稿"""
    if not GROK_API_KEY or not GROK_API_URL:
        logger.warning("缺少 GROK_API_KEY 或 GROK_API_URL，跳過優化")
        return script
    try:
        response = requests.post(
            GROK_API_URL,
            json={'script': script},
            headers={'Authorization': f'Bearer {GROK_API_KEY}'},
            timeout=15
        )
        response.raise_for_status()
        logger.info(f"Grok API 回應: {response.text}")
        improved_script = response.json().get('improved_script', script)
        logger.info("Grok API 優化文字稿成功")
        return improved_script
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

def save_script(script, mode):
    """保存文字稿"""
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'script.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿保存至 {output_path}")

def main(mode='tw', debug=False):
    script = generate_script(mode, debug_data=debug)
    script = improve_with_grok(script)
    save_script(script, mode)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='文字編輯師腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    parser.add_argument('--debug', action='store_true', help='啟用 debug 模式')
    args = parser.parse_args()
    main(args.mode, debug=args.debug)
