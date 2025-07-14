import yfinance as yf
import requests
import json
import yaml
import random
from datetime import datetime, timedelta
from gtts import gTTS
from feedgen.feed import FeedGenerator
import os
import logging

# 設置日誌
def setup_logger():
    os.makedirs("data/logs", exist_ok=True)
    log_file = f"data/logs/podcast_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

# 數據抓取
def fetch_indices():
    indices = ['^DJI', '^IXIC', '^GSPC', '^SOX', 'QQQ', 'SPY']
    data = {}
    for idx in indices:
        try:
            ticker = yf.Ticker(idx)
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                logger.error(f"Failed to fetch data for {idx}")
                return None
            close = hist['Close'][-1]
            prev_close = hist['Close'][-2]
            change = ((close - prev_close) / prev_close) * 100
            data[idx] = {'close': round(close, 2), 'change': round(change, 2)}
            logger.info(f"Fetched {idx}: close={close}, change={change}%")
        except Exception as e:
            logger.error(f"Error fetching {idx}: {str(e)}")
            return None
    return data

def fetch_crypto(api_key):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {'X-CMC_PRO_API_KEY': api_key}
    params = {'symbol': 'BTC'}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()['data']['BTC']['quote']['USD']
        logger.info(f"Fetched BTC: price={data['price']}, change={data['percent_change_24h']}%")
        return {'price': round(data['price'], 2), 'change': round(data['percent_change_24h'], 2)}
    except Exception as e:
        logger.error(f"Error fetching BTC: {str(e)}")
        return None

def fetch_gold():
    try:
        # 模擬 TradingEconomics API（需自行申請）
        data = {'price': 3354.76, 'change': 0.92}  # 假設數據
        logger.info(f"Fetched Gold: price={data['price']}, change={data['change']}%")
        return data
    except Exception as e:
        logger.error(f"Error fetching Gold: {str(e)}")
        return None

def fetch_top_stocks():
    try:
        # 模擬 Yahoo Finance（需自行實現）
        stocks = ['WLGS', 'ABVE', 'BTOG', 'NCNA', 'OPEN']
        logger.info(f"Fetched top stocks: {stocks}")
        return stocks
    except Exception as e:
        logger.error(f"Error fetching top stocks: {str(e)}")
        return None

def fetch_news(api_key):
    try:
        # 模擬 NewsAPI（需自行申請）
        news = {
            'ai': {'title': 'Capgemini收購WNS', 'summary': '以33億美元強化企業AI能力，AI市場競爭更火熱！'},
            'economic': {'title': '美國經濟增長放緩', 'summary': '聯準會降息預期降溫，市場繃緊神經！'}
        }
        logger.info(f"Fetched news: AI={news['ai']['title']}, Economic={news['economic']['title']}")
        return news
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        return None

def fetch_quote():
    try:
        with open('data/quotes.json', 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        quote = random.choice(quotes)
        logger.info(f"Fetched quote: {quote['text']}")
        return quote
    except Exception as e:
        logger.error(f"Error fetching quote: {str(e)}")
        return None

# 生成腳本
def generate_script(cmc_api_key, newsapi_key):
    try:
        with open('podcast_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            tw_phrases = json.load(f)

        indices = fetch_indices() or {
            '^DJI': {'close': 44371.51, 'change': -0.63},
            '^IXIC': {'close': 20585.53, 'change': -0.22},
            '^GSPC': {'close  ': 6259.75, 'change': -0.33},
            '^SOX': {'close': 569
