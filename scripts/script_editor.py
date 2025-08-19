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

# ===== 設定日誌 =====
logging.basicConfig(
    filename='logs/script_editor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== 配置 Grok API =====
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')  # 假設的 API 端點

# ===== 載入配置 =====
def load_config():
    config_file = 'config.json'
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    rss_url = config.get('rss_url', 'https://tw.stock.yahoo.com/rss?category=news')
    return config, rss_url

# ===== 從 CSV 取得最新收盤數據 =====
def load_market_data(symbol):
    csv_path = os.path.join('data', f'{symbol}.csv')
    if not os.path.exists(csv_path):
        logger.warning(f"缺少 {csv_path}")
        return None
    df = pd.read_csv(csv_path)
    if df.empty:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    close = latest['Close']
    change_pct = ((latest['Close'] - prev['Close']) / prev['Close'] * 100) if prev['Close'] else 0.0
    return {
        'symbol': symbol,
        'close': close,
        'change_pct': round(change_pct, 2)
    }

# ===== 載入策略分析與市場分析 =====
def load_strategy(symbol):
    path = os.path.join('data', f'strategy_best_{symbol}.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_market_analysis(symbol):
    path = os.path.join('data', f'market_analysis_{symbol}.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ===== 抓取新聞 =====
def fetch_news(rss_url, keywords, max_news=3):
    try:
        resp = requests.get(rss_url, timeout=10)
        feed = parse(resp.text)
        news = []
        for entry in feed.entries:
            if any(k in entry.title for k in keywords):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.published
                })
            if len(news) >= max_news:
                break
        news.sort(key=lambda x: x['published'], reverse=True)
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

# ===== 生成 AI 投資機會 =====
def generate_ai_opportunities(mode):
    ai_topics = [
        "AI 智能交易平台",
        "生成式 AI 內容公司",
        "AI 芯片與硬體加速",
        "人工智慧雲端服務",
        "自動駕駛與 AI 感測器"
    ]
    count = 2 if mode == 'tw' else 3
    return random.sample(ai_topics, count)

# ===== 生成文字稿 =====
def generate_script(mode, config):
    today = datetime.now().strftime("%Y-%m-%d")
    rss_url = config.get('rss_url')
    keywords = ['經濟','半導體'] if mode == 'tw' else ['economy','semiconductor']
    main_symbol = '0050.TW' if mode == 'tw' else 'QQQ'
    
    # 市場資料
    market_symbols = [main_symbol]
    if mode == 'tw':
        market_symbols.append('^TWII')
    else:
        market_symbols += ['^DJI','^IXIC','^GSPC','SPY','BTC-USD','GC=F']
    market_data = {s: load_market_data(s) for s in market_symbols}

    # 策略與分析
    strategy = load_strategy(main_symbol)
    analysis = load_market_analysis(main_symbol)

    # 新聞
    news = fetch_news(rss_url, keywords)

    # AI 投資機會
    ai_opps = generate_ai_opportunities(mode)

    # 生成稿件
    script_lines = [f"大家好，這裡是《幫幫忙說台股》" if mode=='tw' else "大家好，這裡是《幫幫忙說美股》", f"日期：{today}\n"]

    # 市場數據播報
    if mode=='tw':
        twii = market_data.get('^TWII')
        if twii:
            script_lines.append(f"台股加權指數收盤 {twii['close']} 點，漲跌幅 {twii['change_pct']}%。")
        main = market_data.get('0050.TW')
        if main:
            script_lines.append(f"0050 今日收盤 {main['close']} 元。")
    else:
        for s in ['^DJI','^IXIC','^GSPC','QQQ','SPY','BTC-USD','GC=F']:
            data = market_data.get(s)
            if data:
                script_lines.append(f"{s} 收盤 {data['close']}，漲跌 {data['change_pct']}%。")

    # 策略與分析播報
    if strategy and analysis:
        script_lines.append(f"\n策略分析師建議使用策略：{strategy.get('best_strategy','N/A')}，參數：{strategy.get('params',{})}。")
        script_lines.append(f"市場分析師建議：{analysis.get('recommendation','N/A')}，倉位 {analysis.get('position_size',0.0)}。")
        if analysis.get('risk_note'):
            script_lines.append(f"風險提醒：{analysis.get('risk_note')}")

    # 新聞摘要
    if news:
        script_lines.append("\n新聞摘要：")
        for n in news:
            script_lines.append(f"- {n['title']} ({n['published']}) {n['link']}")

    # AI 投資機會
    script_lines.append("\nAI 投資機會：")
    for opp in ai_opps:
        script_lines.append(f"- {opp}")

    # 鼓勵語
    quotes = [
        "投資成功的關鍵是耐心。",
        "股市短期波動，長期才是致勝。",
        "風險與報酬永遠並存。"
    ]
    script_lines.append(f"\n記住 Kostolany 說過：『{random.choice(quotes)}』")

    return "\n".join(script_lines)

# ===== Grok API 優化 =====
def improve_script_grok(script):
    if not GROK_API_KEY or not GROK_API_URL:
        logger.warning("Grok API 金鑰或 URL 未設定，跳過優化")
        return script
    try:
        resp = requests.post(
            GROK_API_URL,
            json={"script": script},
            headers={"Authorization": f"Bearer {GROK_API_KEY}"}
        )
        resp.raise_for_status()
        improved = resp.json().get('improved_script', script)
        return improved
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

# ===== 儲存文字稿 =====
def save_script(script, mode):
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'script.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿已保存: {path}")

# ===== 主程式 =====
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='文字編輯師腳本')
    parser.add_argument('--mode', default='tw', choices=['tw','us'], help='播客模式 (tw/us)')
    args = parser.parse_args()

    config, rss_url = load_config()
    raw_script = generate_script(args.mode, config)
    final_script = improve_script_grok(raw_script)
    save_script(final_script, args.mode)
    print(f"🎙️ 文字稿生成完成 for {args.mode}")