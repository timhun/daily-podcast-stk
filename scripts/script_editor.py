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
logging.basicConfig(filename='logs/script_editor.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        return rss_url, config.get('news_keywords', ['經濟', '半導體']), config.get('symbols', {'tw': '0050.TW', 'us': 'QQQ'}).get(mode, '0050.TW')
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
        news.sort(key=lambda x: x['published'], reverse=True)  # 按時間排序，確保最新
        logger.info(f"RSS 抓取結果: {len(news)} 則新聞 - {', '.join([n['title'] for n in news])}")
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

def load_analysis(symbol):
    """載入市場分析結果"""
    analysis_path = os.path.join('data', f'market_analysis_{symbol}.json')
    if not os.path.exists(analysis_path):
        logger.error(f"缺少 {analysis_path}")
        return {}
    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        logger.info(f"載入分析結果: {analysis.get('recommendation', 'N/A')}, 倉位 {analysis.get('position_size', 0.0)}")
        return analysis
    except Exception as e:
        logger.error(f"載入 {symbol} 分析結果失敗: {e}")
        return {}

def generate_script(analysis, news, mode):
    """生成 podcast 文字稿模板"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    market_name = "台股" if mode == 'tw' else "美股"

    script = f"歡迎收聽 {market_name} podcast！今天是 {date_str}。\n\n"
    script += f"市場建議: {analysis.get('recommendation', 'N/A')}，倉位 {analysis.get('position_size', 0.0)}。\n"
    script += "新聞摘要:\n"
    for n in news:
        script += f"- {n['title']} ({n['published']}) {n['link']}\n"
    script += "\n感謝收聽！"

    logger.info(f"生成文字稿摘要: 長度 {len(script)} 字元, 新聞數 {len(news)}")
    return script

def improve_with_grok(script):
    """使用 Grok API 優化文字稿"""
    if not GROK_API_KEY:
        logger.warning("缺少 GROK_API_KEY，跳過優化")
        return script
    try:
        response = requests.post(GROK_API_URL, json={'script': script}, headers={'Authorization': f'Bearer {GROK_API_KEY}'})
        response.raise_for_status()
        improved_script = response.json().get('improved_script', script)
        logger.info(f"Grok API 回應: 優化文字稿成功")
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
    """主函數，執行文字編輯"""
    rss_url, keywords, symbol = load_config(mode)
    news = fetch_rss_news(rss_url, keywords)
    analysis = load_analysis(symbol)
    script = generate_script(analysis, news, mode)
    improved_script = improve_with_grok(script)
    save_script(improved_script, mode)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='文字編輯師腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    args = parser.parse_args()
    main(args.mode)
