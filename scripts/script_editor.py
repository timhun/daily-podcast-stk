# scripts/script_editor.py
import feedparser
import json
import os
import sys
from utils import setup_json_logger, get_grok_client, get_taiwan_time, slack_alert
import pandas as pd
import random

logger = setup_json_logger('script_editor')

def translate_news(news, client):
    prompt = f"Translate to Traditional Chinese with Taiwanese terms: {json.dumps(news)}"
    response = client.chat.completions.create(model="grok-4-mini", messages=[{"role": "user", "content": prompt}])
    return json.loads(response.choices[0].message.content)

def main(mode=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    if not mode:
        slack_alert("Mode not specified")
        return
    
    today_str = get_taiwan_time().strftime('%Y%m%d')
    focus_symbol = 'QQQ' if mode == 'us' else '0050.TW'
    clean_symbol = focus_symbol.replace('.', '').replace('^', '')
    
    analysis_file = f"data/market_analysis_{clean_symbol}.json"
    if not os.path.exists(analysis_file):
        slack_alert(f"Missing analysis for {focus_symbol}")
        return
    
    with open(analysis_file, 'r') as f:
        analysis = json.load(f)
    
    data = {}
    for sym in config['symbols'][mode]:
        file = f"data/daily_{sym.replace('.', '_').replace('^', '')}.csv"
        if os.path.exists(file):
            df = pd.read_csv(file, index_col='Date', parse_dates=True)
            latest = df.iloc[-1]
            data[sym] = {'Close': latest['Close'], 'Change': (latest['Close'] - latest['Open']) / latest['Open']}
    
    client = get_grok_client()
    news = []
    rss_url = config['rss_url_us' if mode == 'us' else 'rss_url_tw']
    feed = feedparser.parse(rss_url)
    for entry in feed.entries:
        if len(news) >= config['news_limit']:
            break
        if any(cat in entry.title or cat in entry.summary for cat in config['news_categories']):
            news_item = {"title": entry.title, "summary": entry.summary}
            if mode == 'us':
                news_item = translate_news(news_item, client)
            news.append(news_item)
    
    prompt = f"""
    Generate a Traditional Chinese podcast script for {config['podcast_title_' + mode]}.
    Host: {config['host_name']}. Structure:
    {'1. TWII: {data["^TWII"]["Close"]} ({data["^TWII"]["Change"]:.2%})
2. 0050: {data["0050.TW"]["Close"]}
3. 0050 Strategy: {json.dumps(analysis)}
4. News: {json.dumps(news)}
5. Quote: Random from {config["kosto_quotes"]}' if mode == 'tw' else
    '1. DJI: {data["^DJI"]["Close"]} ({data["^DJI"]["Change"]:.2%}), IXIC: {data["^IXIC"]["Close"]} ({data["^IXIC"]["Change"]:.2%}), GSPC: {data["^GSPC"]["Close"]} ({data["^GSPC"]["Change"]:.2%})
2. QQQ: {data["QQQ"]["Close"]}, SPY: {data["SPY"]["Close"]}, BTC: {data["BTC-USD"]["Close"]}, GC: {data["GC=F"]["Close"]}
3. QQQ Strategy: {json.dumps(analysis)}
4. News: {json.dumps(news)}
5. Quote: Random from {config["kosto_quotes"]}'} 
    Rules: TW Chinese, <2300 words, Taiwanese terms, AI terms in English, content only.
    """
    
    response = client.chat.completions.create(model=config['grok_model'], messages=[{"role": "user", "content": prompt}])
    script = response.choices[0].message.content.strip()
    
    dir_path = f"docs/podcast/{today_str}_{mode}"
    os.makedirs(dir_path, exist_ok=True)
    with open(f"{dir_path}/script.txt", 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info(json.dumps({"mode": mode, "word_count": len(script)}))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['us', 'tw'] else None
    main(mode)
