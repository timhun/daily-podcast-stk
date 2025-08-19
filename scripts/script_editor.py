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
logging.basicConfig(filename='logs/script_editor.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')  # 假設的 API 端點

def load_config(mode=None):
    """載入配置檔案 config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    rss_url = config.get('rss_url', 'https://tw.stock.yahoo.com/rss?category=news')
    keywords = config.get('news_keywords', ['經濟', '半導體'])
    symbol = config.get('symbols', {'tw':'0050.TW','us':'QQQ'}).get(mode, '0050.TW')
    return rss_url, keywords, symbol

def fetch_rss_news(rss_url, keywords, max_news=3):
    """抓取最新 3 則新聞，篩選關鍵字"""
    try:
        feed = parse(requests.get(rss_url, timeout=10).text)
        news = [e for e in feed.entries if any(k in e.title for k in keywords)]
        news.sort(key=lambda x: x.published, reverse=True)
        news = news[:max_news]
        logger.info(f"抓取新聞: {len(news)} 則")
        return news
    except Exception as e:
        logger.error(f"RSS 失敗: {e}")
        return []

def load_latest_data(symbol):
    """讀取最新市場資料 (CSV)"""
    path = os.path.join('data', f'daily_{symbol}.csv')
    if not os.path.exists(path):
        logger.error(f"缺少資料檔: {path}")
        return None
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    latest = df.iloc[-1].to_dict()
    logger.info(f"{symbol} 最新收盤: {latest.get('Close','N/A')}")
    return latest

def load_analysis(symbol):
    """讀取市場分析師建議"""
    path = os.path.join('data', f'market_analysis_{symbol}.json')
    if not os.path.exists(path):
        logger.warning(f"缺少分析結果: {path}")
        return {}
    with open(path,'r',encoding='utf-8') as f:
        analysis = json.load(f)
    return analysis

def random_transition():
    """簡單隨機過渡語增加口語化"""
    phrases = [
        "接下來我們來看看",
        "另外值得注意的是",
        "同時關注到",
        "在市場上我們還看到"
    ]
    return random.choice(phrases)

def generate_script(mode='tw'):
    """生成文字稿"""
    rss_url, keywords, symbol = load_config(mode)
    news = fetch_rss_news(rss_url, keywords)
    analysis = load_analysis(symbol)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    script = f"大家好，歡迎收聽《幫幫忙說台股》，今天是 {date_str}，主持人幫幫忙為您帶來最新市場資訊。\n\n"
    
    if mode == 'tw':
        twii = load_latest_data('^TWII')
        etf = load_latest_data('0050.TW')
        if twii:
            script += f"今日台股加權指數收盤 {twii['Close']}，漲跌幅 {twii['Close']-twii['Open']:.2f} 點。\n"
        if etf:
            script += f"{etf['Symbol']} 今日收盤價 {etf['Close']}。\n"
        script += f"{random_transition()}短線策略建議: {analysis.get('recommendation','持倉')}，倉位 {analysis.get('position_size',0.0)}。\n"
    else:
        # 美股模式
        indices = ['^DJI','^IXIC','^GSPC']
        assets = ['QQQ','SPY','BTC','GC']
        for idx in indices:
            data = load_latest_data(idx)
            if data:
                script += f"{idx} 收盤 {data['Close']}, 漲跌 {data['Close']-data['Open']:.2f} 點。\n"
        for a in assets:
            data = load_latest_data(a)
            if data:
                script += f"{a} 收盤價 {data['Close']}。\n"
        script += f"{random_transition()}短線策略建議: {analysis.get('recommendation','持倉')}，倉位 {analysis.get('position_size',0.0)}。\n"
    
    # 新聞摘要
    if news:
        script += "\n最新新聞摘要:\n"
        for n in news:
            script += f"- {n['title']} ({n['published']}) {n['link']}\n"
    
    # 投資鼓勵語
    script += "\n記住 Andre Kostolany 的名言: 市場永遠是對的，但投資者要有耐心與智慧。\n"
    
    logger.info(f"生成文字稿，長度 {len(script)} 字")
    return script

def improve_with_grok(script):
    if not GROK_API_KEY:
        logger.warning("缺少 GROK_API_KEY，跳過優化")
        return script
    try:
        resp = requests.post(GROK_API_URL, json={'script': script}, headers={'Authorization': f'Bearer {GROK_API_KEY}'})
        resp.raise_for_status()
        return resp.json().get('improved_script', script)
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

def save_script(script, mode):
    date_str = datetime.now().strftime("%Y%m%d")
    path = os.path.join('docs','podcast',f"{date_str}_{mode}")
    os.makedirs(path, exist_ok=True)
    output_file = os.path.join(path,'script.txt')
    with open(output_file,'w',encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿保存至 {output_file}")

if __name__=='__main__':
    parser = argparse.ArgumentParser(description="文字編輯師")
    parser.add_argument('--mode',default='tw',choices=['tw','us'])
    args = parser.parse_args()
    script = generate_script(args.mode)
    script = improve_with_grok(script)
    save_script(script,args.mode)