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
GROK_API_URL = os.getenv('GROK_API_URL')  # 假設的 API 端點

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
        keywords = ['經濟', '半導體']
        symbol_map = {'tw': '0050.TW', 'us': 'QQQ'}
        symbol = symbol_map.get(mode, '0050.TW')
        return rss_url, keywords, symbol
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
                    'published': entry.published
                })
            if len(news) >= max_news:
                break
        news.sort(key=lambda x: x['published'], reverse=True)
        logger.info(f"RSS 抓取結果: {len(news)} 則新聞 - {', '.join([n['title'] for n in news])}")
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

def load_analysis(symbol):
    """載入市場分析師與策略管理師資料"""
    market_path = os.path.join('data', f'market_analysis_{symbol}.json')
    strategy_path = os.path.join('data', f'strategy_best_{symbol}.json')
    market = {}
    strategy = {}
    try:
        if os.path.exists(market_path):
            with open(market_path, 'r', encoding='utf-8') as f:
                market = json.load(f)
        if os.path.exists(strategy_path):
            with open(strategy_path, 'r', encoding='utf-8') as f:
                strategy = json.load(f)
        return market, strategy
    except Exception as e:
        logger.error(f"載入 {symbol} 分析或策略資料失敗: {e}")
        return {}, {}

def load_latest_price(symbol):
    """從 data 目錄取最新收盤價"""
    path = os.path.join('data', f'daily_{symbol}.csv')
    if not os.path.exists(path):
        logger.warning(f"缺少 {path}")
        return None
    try:
        df = pd.read_csv(path)
        df['Date'] = pd.to_datetime(df['Date'])
        latest = df.iloc[-1]
        return latest
    except Exception as e:
        logger.error(f"讀取 {symbol} CSV 失敗: {e}")
        return None

def generate_script(mode):
    """生成 podcast 文字稿"""
    rss_url, keywords, symbol = load_config(mode)
    news = fetch_rss_news(rss_url, keywords)
    market, strategy = load_analysis(symbol)
    latest_price = load_latest_price(symbol)

    date_str = datetime.now().strftime("%Y-%m-%d")
    market_name = "台股" if mode == 'tw' else "美股"

    # 隨機模板
    templates = [
        "歡迎收聽《幫幫忙說台股》，今天是 {date}。",
        "大家好，這裡是《幫幫忙說台股》，日期：{date}。",
        "嗨！我是幫幫忙，今天帶來 {market_name} 的最新資訊，日期 {date}。"
    ]
    intro = random.choice(templates).format(date=date_str, market_name=market_name)

    # 市場建議與策略
    recommendation_text = ""
    if market:
        recommendation_text += f"主角標的 {symbol} 市場建議：{market.get('recommendation', '持倉')}，倉位 {market.get('position_size', 0.0)*100:.0f}%。\n"
        recommendation_text += f"市場分析師觀察：{market.get('risk_note', '')}\n"
    if strategy:
        params_str = ', '.join([f"{k}={v}" for k, v in strategy.get('params', {}).items()])
        recommendation_text += f"策略師建議：依據 {strategy.get('best_strategy','N/A')} 模型 ({params_str})，預期報酬約 {strategy.get('return_pct',0):.2f}%，基準報酬 {strategy.get('baseline_pct',0):.2f}%。\n"

    # 最新收盤價
    price_text = ""
    if latest_price is not None:
        price_text += f"{symbol} 最新收盤價: {latest_price['Close']}\n"

    # 新聞
    news_text = "新聞摘要:\n"
    for n in news:
        news_text += f"- {n['title']} ({n['published']}) {n['link']}\n"

    # 收尾金句
    closing_quotes = [
        "記住 Kostolany 說過：『投資成功的關鍵是耐心。』",
        "Kostolany 教導我們：『市場永遠是對的。』",
        "投資有風險，但記得 Kostolany 的名言：『恐懼和貪婪永遠主宰市場。』"
    ]
    closing = random.choice(closing_quotes)

    script = "\n".join([intro, price_text, recommendation_text, news_text, closing])

    # Grok 優化
    script = improve_with_grok(script)

    return script

def improve_with_grok(script):
    """使用 Grok API 優化文字稿"""
    if not GROK_API_KEY or not GROK_API_URL:
        logger.warning("缺少 GROK_API_KEY 或 GROK_API_URL，跳過優化")
        return script
    try:
        response = requests.post(GROK_API_URL, json={'script': script}, headers={'Authorization': f'Bearer {GROK_API_KEY}'}, timeout=15)
        response.raise_for_status()
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
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info(f"文字稿保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存文字稿失敗: {e}")

def main(mode='tw'):
    script = generate_script(mode)
    save_script(script, mode)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='文字編輯師腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    args = parser.parse_args()
    main(args.mode)