# scripts/script_editor.py
import pandas as pd
import json
import os
from datetime import datetime
import logging
import requests
from feedparser import parse
import argparse

# ===== 設定日誌 =====
logging.basicConfig(
    filename='logs/script_editor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== Grok API =====
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = os.getenv('GROK_API_URL')

# ===== 載入 config =====
def load_config():
    config_file = 'config.json'
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# ===== 讀取市場 CSV =====
def load_market_csv(mode='tw'):
    market_data = {}
    tickers = ['^DJI','^IXIC','^GSPC','QQQ','SPY','BTC-USD','GC=F'] if mode=='us' else ['^TWII','0050.TW']
    for ticker in tickers:
        csv_file = os.path.join('data', f'{ticker}.csv')
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                last = df.iloc[-1]
                close = last.get('Close', None)
                open_price = last.get('Open', close)
                change_pct = round(((close - open_price)/open_price)*100, 2) if close and open_price else 0.0
                market_data[ticker] = {'Close': round(close,2), 'ChangePct': change_pct}
            except Exception as e:
                logger.error(f"讀取 {csv_file} 失敗: {e}")
                market_data[ticker] = {'Close': None, 'ChangePct': 0.0}
        else:
            logger.warning(f"缺少 CSV 檔案: {csv_file}")
            market_data[ticker] = {'Close': None, 'ChangePct': 0.0}
    return market_data

# ===== 讀取策略與市場分析結果 =====
def load_analysis(symbol):
    strategy_file = os.path.join('data', f'strategy_best_{symbol}.json')
    market_file = os.path.join('data', f'market_analysis_{symbol}.json')
    strategy, market = {}, {}
    if os.path.exists(strategy_file):
        with open(strategy_file, 'r', encoding='utf-8') as f:
            strategy = json.load(f)
    if os.path.exists(market_file):
        with open(market_file, 'r', encoding='utf-8') as f:
            market = json.load(f)
    return strategy, market

# ===== RSS 抓新聞 =====
def fetch_rss_news(rss_url, keywords, max_news=3):
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        feed = parse(response.text)
        news = []
        for entry in feed.entries:
            if any(k in entry.title for k in keywords):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', '')
                })
            if len(news)>=max_news:
                break
        return news
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

# ===== Grok 優化文字稿 =====
def improve_with_grok(script):
    if not GROK_API_KEY or not GROK_API_URL:
        logger.warning("缺少 GROK API，跳過優化")
        return script
    try:
        response = requests.post(GROK_API_URL,
                                 json={'script': script},
                                 headers={'Authorization': f'Bearer {GROK_API_KEY}'},
                                 timeout=15)
        response.raise_for_status()
        return response.json().get('improved_script', script)
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

# ===== 生成文字稿 =====
def generate_script(mode='tw', debug=False):
    config = load_config()
    rss_url = config.get('rss_url')
    keywords = ['經濟','半導體'] if mode=='tw' else ['AI','科技']
    symbol = '0050.TW' if mode=='tw' else 'QQQ'

    # 讀市場數據
    market_data = load_market_csv(mode)
    strategy, market = load_analysis(symbol)
    news = fetch_rss_news(rss_url, keywords, max_news=3)

    date_str = datetime.now().strftime("%Y-%m-%d")
    script = f"大家好，這裡是《幫幫忙說{'台股' if mode=='tw' else '美股'}》\n日期：{date_str}\n\n"

    # 市場概況
    for k,v in market_data.items():
        script += f"{k} 收盤 {v['Close']}，漲跌 {v['ChangePct']}%。\n"

    script += "\n焦點標的分析：\n"
    script += f"策略分析師建議使用策略：{strategy.get('best_strategy','N/A')}，參數：{strategy.get('params',{})}\n"
    script += f"市場分析師建議：{market.get('recommendation','N/A')}，倉位 {market.get('position_size',0.0)}。\n"
    if market.get('risk_note'):
        script += f"風險提醒：{market.get('risk_note')}\n"

    # 新聞摘要
    script += "\n新聞摘要:\n"
    for n in news:
        script += f"- {n['title']} ({n['published']}) {n['link']}\n"

    # AI 投資機會
    script += "\nAI 投資機會:\n"
    if mode=='us':
        script += "- 人工智慧雲端服務\n- AI 芯片與硬體加速\n- AI 智能交易平台\n"
    else:
        script += "- 台灣 AI 新創公司\n- AI ETF 或半導體應用\n"

    script += "\n記住 Kostolany 說過：『股市短期波動，長期才是致勝。』\n"

    if debug:
        logger.info("==== DEBUG ====")
        logger.info("市場數據: %s", market_data)
        logger.info("策略: %s", strategy)
        logger.info("市場分析師: %s", market)
        logger.info("新聞: %s", news)

    # Grok 優化
    script = improve_with_grok(script)
    return script

# ===== 保存文字稿 =====
def save_script(script, mode):
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs','podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir,'script.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info(f"文字稿保存至 {output_path}")

# ===== 主函數 =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='tw', choices=['tw','us'], help='播客模式 tw/us')
    parser.add_argument('--debug', action='store_true', help='啟用 debug 模式')
    args = parser.parse_args()
    script = generate_script(args.mode, debug=args.debug)
    save_script(script, args.mode)
    print("✅ 文字稿生成完成")