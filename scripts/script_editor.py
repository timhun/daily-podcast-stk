# scripts/script_editor.py
import feedparser
import json
import os
import logging
from openai import OpenAI
from datetime import datetime, timedelta
import pytz
import pandas as pd
import random

logging.basicConfig(filename='logs/script_editor.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def get_latest_news(rss_url, categories, limit):
    feed = feedparser.parse(rss_url)
    news = []
    now = datetime.now(pytz.utc)
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
        if (now - pub_date) <= timedelta(hours=24):
            if any(cat in entry.title or cat in entry.summary for cat in categories):
                news.append({"title": entry.title, "summary": entry.summary, "link": entry.link})
        if len(news) >= limit:
            break
    return news

def generate_script(mode, config, analysis, data, news):
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ['GROK_API_KEY'])
    
    if mode == 'tw':
        twii_close = data['^TWII']['Close']
        twii_change = data['^TWII']['Change']
        etf_close = data['0050.TW']['Close']
        
        prompt = f"""
        生成繁體中文播客逐字稿，節目名稱：{config['podcast_title_tw']}，主持人：{config['host_name']}。
        結構：
        1. 今日台股加權指數收盤：{twii_close}點，漲跌幅：{twii_change:.2%}。
        2. 0050收盤價：{etf_close}。
        3. 針對0050短線策略：{analysis}。
        4. 三則新聞：{news}，每則加重點說明。
        5. 結尾：{random.choice(config['kosto_quotes'])}。
        注意：繁體中文、台灣用語、<3000字、僅輸出正文。
        """
    
    elif mode == 'us':
        dji_close = data['^DJI']['Close']
        dji_change = data['^DJI']['Change']
        nasdaq_close = data['^IXIC']['Close']
        nasdaq_change = data['^IXIC']['Change']
        sp_close = data['^GSPC']['Close']
        sp_change = data['^GSPC']['Change']
        qqq_close = data['QQQ']['Close']
        spy_close = data['SPY']['Close']
        btc_close = data['BTC-USD']['Close']
        gc_close = data['GC=F']['Close']
        
        prompt = f"""
        生成繁體中文播客逐字稿，節目名稱：{config['podcast_title_us']}，主持人：{config['host_name']}。
        結構：
        1. 美股大盤：道瓊{dji_close}點({dji_change:.2%})，Nasdaq {nasdaq_close}點({nasdaq_change:.2%})，S&P500 {sp_close}點({sp_change:.2%})。
        2. QQQ：{qqq_close}，SPY：{spy_close}，BTC：{btc_close}，黃金：{gc_close}。
        3. 針對QQQ短線策略：{analysis}。
        4. 結尾：{random.choice(config['kosto_quotes'])}。
        注意：繁體中文、台灣用語、<3000字、僅輸出正文。
        """
    
    response = client.chat.completions.create(
        model=config['grok_model'],
        messages=[{"role": "user", "content": prompt}]
    )
    script = response.choices[0].message.content.strip()
    logging.info(f"Generated script length: {len(script)}")
    return script

def get_latest_data(mode):
    data = {}
    symbols = json.load(open('config.json'))['symbols'][mode]
    for sym in symbols:
        file = f"data/daily_{sym.replace('.', '_').replace('^', '')}.csv"
        if os.path.exists(file):
            df = pd.read_csv(file, index_col='Date', parse_dates=True)
            latest = df.iloc[-1]
            change = (latest['Close'] - latest['Open']) / latest['Open']
            data[sym] = {'Close': latest['Close'], 'Change': change}
    return data

def main(mode_input=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    tw_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tw_tz)
    today_str = now.strftime('%Y%m%d')
    
    if mode_input:
        mode = mode_input
    else:
        mode = 'us' if now.hour < 12 else 'tw'
    
    focus_sym = '0050TW' if mode == 'tw' else 'QQQ'
    analysis_file = f"data/market_analysis_{focus_sym}.json"
    if not os.path.exists(analysis_file):
        logging.error(f"Missing analysis for {focus_sym}")
        return
    
    with open(analysis_file, 'r') as f:
        analysis = json.dumps(json.load(f))
    
    data = get_latest_data(mode)
    
    news = []
    if mode == 'tw':
        news = get_latest_news(config['rss_url'], config['news_categories'], config['news_limit'])
        news_str = json.dumps(news)
    else:
        news_str = ""  # US no news in remark
    
    script = generate_script(mode, config, analysis, data, news_str)
    
    dir_path = f"docs/podcast/{today_str}_{mode}"
    os.makedirs(dir_path, exist_ok=True)
    script_file = f"{dir_path}/script.txt"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script)
    logging.info(f"Saved script to {script_file}")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    main(mode)
