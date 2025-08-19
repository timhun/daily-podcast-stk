# scripts/script_editor.py
import pandas as pd
import json
import os
from datetime import datetime
import logging
import requests
from feedparser import parse
import argparse
import random

# 設定日誌
logging.basicConfig(filename='logs/script_editor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 Grok API
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')

# 主角標的
MAIN_SYMBOLS = {'tw': '0050.TW', 'us': 'QQQ'}

# 美股大盤與資產
US_MARKET_SYMBOLS = ['^DJI', '^IXIC', '^GSPC', 'QQQ', 'SPY', 'BTC-USD', 'GC=F']

def load_config():
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    rss_url = config.get('rss_url', 'https://tw.stock.yahoo.com/rss?category=news')
    keywords = config.get('news_keywords', ['經濟', '半導體'])
    return rss_url, keywords

def fetch_rss_news(rss_url, keywords, max_news=3):
    """從 RSS 抓取最新新聞，篩選關鍵字"""
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        feed = parse(response.text)
        news = []
        for entry in feed.entries:
            title = entry.title
            if any(k in title for k in keywords):
                news.append({'title': title, 'link': entry.link, 'published': entry.published})
            if len(news) >= max_news:
                break
        news.sort(key=lambda x: x['published'], reverse=True)
        logger.info(f"抓取 {len(news)} 則新聞")
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"讀取 {file_path} 失敗: {e}")
    else:
        logger.warning(f"找不到檔案: {file_path}")
    return {}

def load_latest_prices(symbols):
    """讀取 CSV 最新收盤價與漲跌幅"""
    latest_prices = {}
    for sym in symbols:
        csv_path = os.path.join('data', f"{sym}.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if 'Close' in df.columns and 'Date' in df.columns:
                    last_row = df.iloc[-1]
                    prev_row = df.iloc[-2] if len(df) > 1 else last_row
                    close = round(last_row['Close'], 2)
                    pct = round((close - prev_row['Close']) / prev_row['Close'] * 100 if prev_row['Close'] else 0.0, 2)
                    latest_prices[sym] = {'close': close, 'change_pct': pct}
            except Exception as e:
                logger.error(f"讀取 {csv_path} 失敗: {e}")
        else:
            logger.warning(f"找不到 CSV: {csv_path}")
    return latest_prices

def generate_podcast_text(strategy, market, news, mode, latest_us=None):
    """生成文字稿"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    main_symbol = MAIN_SYMBOLS[mode]
    script = f"大家好，這裡是《幫幫忙說台股》播客，日期：{date_str}。\n\n"

    # 市場分析
    script += f"{main_symbol} 建議: {market.get('recommendation','N/A')}，倉位 {market.get('position_size',0.0)}。\n"
    if 'risk_note' in market:
        script += f"風險提醒: {market['risk_note']}\n"
    if strategy:
        script += f"最佳策略: {strategy.get('best_strategy','N/A')}，預期報酬: {strategy.get('return_pct','N/A')}%\n"

    # 美股模式加上大盤與資產收盤
    if mode == 'us' and latest_us:
        script += "\n今天美股收盤行情如下：\n"
        for sym in ['^DJI','^IXIC','^GSPC']:
            data = latest_us.get(sym,{})
            script += f"- {sym} 收盤 {data.get('close','N/A')}，漲跌 {data.get('change_pct','N/A')}%\n"
        script += "主要資產收盤價：\n"
        for sym in ['QQQ','SPY','BTC-USD','GC=F']:
            data = latest_us.get(sym,{})
            script += f"- {sym} 收盤 {data.get('close','N/A')}，漲跌 {data.get('change_pct','N/A')}%\n"

    # 新聞摘要
    if news:
        script += "\n新聞摘要:\n"
        for n in news:
            script += f"- {n['title']} ({n['published']}) {n['link']}\n"

    # 投資金句
    quotes = [
        "記住 Kostolany 說過：『投資成功的關鍵是耐心。』",
        "Kostolany 曾提醒：『市場永遠是對的，即使我們不同意。』",
        "Andre Kostolany:『股市不是賺快錢，而是耐心的遊戲。』"
    ]
    script += f"\n{random.choice(quotes)}\n"
    return script

def improve_with_grok(script):
    if not GROK_API_KEY:
        logger.warning("缺少 GROK_API_KEY，跳過優化")
        return script
    try:
        response = requests.post(GROK_API_URL, json={'script': script},
                                 headers={'Authorization': f'Bearer {GROK_API_KEY}'}, timeout=10)
        response.raise_for_status()
        return response.json().get('improved_script', script)
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

def save_script(script, mode):
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs','podcast',f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir,'script.txt')
    with open(path,'w',encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿保存至 {path}")

def main(mode='tw'):
    rss_url, keywords = load_config()
    news = fetch_rss_news(rss_url, keywords)
    main_symbol = MAIN_SYMBOLS[mode]

    # 策略管理師
    strategy_file = os.path.join('data', f"strategy_best_{main_symbol}.json")
    strategy = load_json(strategy_file)

    # 市場分析師
    market_file = os.path.join('data', f"market_analysis_{main_symbol}.json")
    market = load_json(market_file)

    # 美股收盤資料
    latest_us = load_latest_prices(US_MARKET_SYMBOLS) if mode=='us' else None

    # 生成文字稿
    script = generate_podcast_text(strategy, market, news, mode, latest_us)
    script = improve_with_grok(script)
    save_script(script, mode)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='文字編輯師')
    parser.add_argument('--mode', default='tw', choices=['tw','us'], help='播客模式')
    args = parser.parse_args()
    main(args.mode)