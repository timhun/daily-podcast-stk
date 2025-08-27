import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
import json
import datetime
from loguru import logger
from retry import retry
from transformers import pipeline
import pandas as pd

# Configure logging
logger.add("logs/data_collector.log", rotation="1 MB")

# Symbol configuration from project design
SYMBOLS = {
    'us': ['^GSPC', 'QQQ', 'NVDA', '^DJI', '^IXIC', 'SPY', 'AAPL', '^VIX', 'BTC-USD', 'ETH-USD', 'GC=F', 'CL=F'],
    'tw': ['^TWII', '0050.TW', '2330.TW', '2454.TW', '3008.TW']
}

# News sources from project design
NEWS_SOURCES = {
    'us': [
        'https://feeds.bloomberg.com/technology/news.rss',
        'https://www.reddit.com/r/investing/.rss'
    ],
    'tw': [
        'https://tw.stock.yahoo.com/rss?category=news',
        'https://feed.cnyes.com/news/tech'
    ]
}

class DataQualityChecker:
    def __init__(self):
        self.quality_thresholds = {
            'completeness': 0.95,  # >95% data availability
            'freshness_hours': 4,  # Data <4 hours old
            'volatility_threshold': 0.1  # Max allowed change
        }

    def check_completeness(self, data, expected_keys):
        total = len(expected_keys)
        present = sum(1 for key in expected_keys if key in data and data[key])
        return present / total if total > 0 else 0

    def check_freshness(self, data_timestamp):
        now = datetime.datetime.now(datetime.timezone.utc)
        age_hours = (now - data_timestamp).total_seconds() / 3600
        return age_hours <= self.quality_thresholds['freshness_hours']

    def check_volatility(self, data, symbol):
        change = abs(data.get(symbol, {}).get('change', 0))
        return change <= self.quality_thresholds['volatility_threshold'] * 100

    def validate(self, data, symbols):
        checks = {
            'completeness': self.check_completeness(data, symbols),
            'freshness': self.check_freshness(datetime.datetime.now(datetime.timezone.utc)),
            'volatility': all(self.check_volatility(data, symbol) for symbol in symbols)
        }
        quality_score = sum(checks.values()) / len(checks)
        if quality_score < 0.8:
            logger.warning(f"Data quality failed: {checks}, score: {quality_score}")
            # Optionally trigger Slack alert (requires slack-sdk)
        return quality_score, checks

@retry(tries=3, delay=1, backoff=2)
def fetch_market_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period='1d')
    if hist.empty:
        logger.error(f"No data for {symbol}")
        return None
    data = {
        'close': hist['Close'].iloc[-1],
        'change': hist['Close'].pct_change().iloc[-1] * 100 if len(hist) > 1 else 0,
        'timestamp': hist.index[-1].astimezone(datetime.timezone.utc)
    }
    return data

@retry(tries=3, delay=1, backoff=2)
def fetch_news(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.find_all('item', limit=3)  # Top 3 news items
    return [{'title': item.title.text, 'description': item.description.text} for item in items if item.title and item.description]

def collect_data(mode):
    # Initialize data structures
    data = {'market': {}, 'news': [], 'sentiment': {}}
    today = datetime.date.today().strftime('%Y-%m-%d')
    output_dir = f"data/news/{today}"
    os.makedirs(output_dir, exist_ok=True)

    # Fetch market data
    for symbol in SYMBOLS.get(mode, []):
        try:
            market_info = fetch_market_data(symbol)
            if market_info:
                data['market'][symbol] = market_info
        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {str(e)}")

    # Save market data to CSV
    market_df = pd.DataFrame.from_dict(data['market'], orient='index')
    market_df.to_csv(f"data/market/daily_{mode}.csv")

    # Fetch news from multiple sources
    for url in NEWS_SOURCES.get(mode, []):
        try:
            news_items = fetch_news(url)
            data['news'].extend(news_items)
        except Exception as e:
            logger.error(f"Failed to fetch news from {url}: {str(e)}")

    # Save news to JSON
    news_path = f"{output_dir}/{mode}_news.json"
    with open(news_path, 'w', encoding='utf-8') as f:
        json.dump(data['news'], f, ensure_ascii=False, indent=2)

    # Basic sentiment analysis on news headlines
    try:
        sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        headlines = [item['title'] for item in data['news']]
        sentiments = sentiment_analyzer(headlines)
        sentiment_score = sum(s['score'] if s['label'] == 'positive' else -s['score'] for s in sentiments) / len(sentiments) if sentiments else 0
        data['sentiment'] = {
            'overall_score': sentiment_score,
            'bullish_ratio': sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments) if sentiments else 0
        }
        # Save sentiment to JSON
        sentiment_path = f"data/sentiment/{today}/social_metrics.json"
        os.makedirs(os.path.dirname(sentiment_path), exist_ok=True)
        with open(sentiment_path, 'w', encoding='utf-8') as f:
            json.dump(data['sentiment'], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}")

    # Validate data quality
    checker = DataQualityChecker()
    quality_score, checks = checker.validate(data['market'], SYMBOLS.get(mode, []))
    data['quality'] = {'score': quality_score, 'checks': checks}

    logger.info(f"Data collected for {mode}: {len(data['market'])} symbols, {len(data['news'])} news items, quality score: {quality_score}")
    return data