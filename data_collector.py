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

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    
# 配置日誌
logger.add("logs/data_collector.log", rotation="1 MB")

SYMBOLS = config['symbols']
NEWS_SOURCES = config['news_sources']

class DataQualityChecker:
    def __init__(self):
        self.quality_thresholds = config['quality_thresholds']

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
            logger.warning(f"數據品質不佳: {checks}, 分數: {quality_score}")
        return quality_score, checks

@retry(tries=3, delay=1, backoff=2)
def fetch_market_data(symbol):
    ticker = yf.Ticker(symbol)
    
    # 每日數據（365 天）
    hist_daily = ticker.history(period='1y')
    if hist_daily.empty:
        logger.error(f"{symbol} 每日數據無回應")
        daily_data = {
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0, 
            'change': 0, 
            'volume': 0, 
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }  # 新增 volume
        daily_df = pd.DataFrame([{
            'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
            'symbol': symbol,
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0,
            'change': 0,
            'volume': 0  # 新增 volume
        }])
    else:
        # 確保索引是 timezone-aware（從之前修復）
        if hist_daily.index.tz is None:
            hist_daily.index = hist_daily.index.tz_localize('Asia/Taipei')
        hist_daily.index = hist_daily.index.tz_convert('UTC')
        daily_data = {
            'open': hist_daily['Open'].iloc[-1],
            'high': hist_daily['High'].iloc[-1],
            'low': hist_daily['Low'].iloc[-1],
            'close': hist_daily['Close'].iloc[-1],
            'close': hist_daily['Close'].iloc[-1],
            'change': hist_daily['Close'].pct_change().iloc[-1] * 100 if len(hist_daily) > 1 else 0,
            'volume': hist_daily['Volume'].iloc[-1],  # 新增 volume
            'timestamp': hist_daily.index[-1]
        }
        daily_df = pd.DataFrame({
            'date': hist_daily.index.strftime('%Y-%m-%d'),
            'symbol': symbol,
            'open': hist_daily['Open'],
            'high': hist_daily['High'],
            'low': hist_daily['Low'],
            'close': hist_daily['Close'],
            'change': hist_daily['Close'].pct_change() * 100,
            'volume': hist_daily['Volume']  # 新增 volume
        }).dropna()

    # 每小時數據（14 天）
    hist_hourly = ticker.history(period='14d', interval='1h')
    if hist_hourly.empty:
        logger.error(f"{symbol} 每小時數據無回應")
        hourly_data = {
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0, 
            'change': 0, 
            'volume': 0, 
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }  # 新增 volume
        hourly_df = pd.DataFrame([{
            'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0,
            'change': 0,
            'volume': 0  # 新增 volume
        }])
    else:
        # 確保索引是 timezone-aware
        if hist_hourly.index.tz is None:
            hist_hourly.index = hist_hourly.index.tz_localize('Asia/Taipei')
        hist_hourly.index = hist_hourly.index.tz_convert('UTC')
        hourly_data = {
            'open': hist_hourly['Open'].iloc[-1],
            'high': hist_hourly['High'].iloc[-1],
            'low': hist_hourly['Low'].iloc[-1],
            'close': hist_hourly['Close'].iloc[-1],
            'change': hist_hourly['Close'].pct_change().iloc[-1] * 100 if len(hist_hourly) > 1 else 0,
            'volume': hist_hourly['Volume'].iloc[-1],  # 新增 volume
            'timestamp': hist_hourly.index[-1]
        }
        hourly_df = pd.DataFrame({
            'date': hist_hourly.index.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'open': hist_hourly['Open'],
            'high': hist_hourly['High'],
            'low': hist_hourly['Low'],
            'close': hist_hourly['Close'],
            'change': hist_hourly['Close'].pct_change() * 100,
            'volume': hist_hourly['Volume']  # 新增 volume
        }).dropna()

    return daily_data, daily_df, hourly_data, hourly_df    
    
@retry(tries=3, delay=1, backoff=2)
def fetch_news(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item', limit=3)  # 每個來源抓取最多 3 則新聞
        return [{'title': item.title.text, 'description': item.description.text} for item in items if item.title and item.description]
    except Exception as e:
        logger.error(f"抓取新聞 {url} 失敗: {str(e)}")
        return []

def collect_data(mode):
    # 初始化數據結構
    data = {'market': {}, 'news': [], 'sentiment': {}}
    today = datetime.date.today().strftime('%Y-%m-%d')
    output_dir = f"data/news/{today}"
    market_dir = "data/market"
    os.makedirs(market_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 抓取市場數據
    for symbol in SYMBOLS.get(mode, []):
        try:
            daily_data, daily_df, hourly_data, hourly_df = fetch_market_data(symbol)
            data['market'][symbol] = daily_data
            
            # 儲存每日數據
            daily_file = f"{market_dir}/daily_{symbol.replace('^', '').replace('.', '_')}.csv"
            daily_df.to_csv(daily_file, index=False)
            logger.info(f"每日數據儲存至: {daily_file}")

            # 儲存每小時數據
            hourly_file = f"{market_dir}/hourly_{symbol.replace('^', '').replace('.', '_')}.csv"
            hourly_df.to_csv(hourly_file, index=False)
            logger.info(f"每小時數據儲存至: {hourly_file}")
        except Exception as e:
            logger.error(f"抓取 {symbol} 市場數據失敗: {str(e)}")
            data['market'][symbol] = {'close': 0, 'change': 0}

    # 從多個來源抓取新聞
    for url in NEWS_SOURCES.get(mode, []):
        news_items = fetch_news(url)
        data['news'].extend(news_items)

    # 儲存新聞到 JSON
    news_path = f"{output_dir}/{mode}_news.json"
    with open(news_path, 'w', encoding='utf-8') as f:
        json.dump(data['news'], f, ensure_ascii=False, indent=2)
    logger.info(f"新聞數據儲存至: {news_path}")

    # 新聞標題情緒分析
    try:
        sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        headlines = [item['title'] for item in data['news']]
        sentiments = sentiment_analyzer(headlines)
        sentiment_score = sum(s['score'] if s['label'] == 'positive' else -s['score'] for s in sentiments) / len(sentiments) if sentiments else 0
        data['sentiment'] = {
            'overall_score': sentiment_score,
            'bullish_ratio': sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments) if sentiments else 0
        }
        # 儲存情緒分析到 JSON
        sentiment_path = f"data/sentiment/{today}/social_metrics.json"
        os.makedirs(os.path.dirname(sentiment_path), exist_ok=True)
        with open(sentiment_path, 'w', encoding='utf-8') as f:
            json.dump(data['sentiment'], f, ensure_ascii=False, indent=2)
        logger.info(f"情緒數據儲存至: {sentiment_path}")
    except Exception as e:
        logger.error(f"情緒分析失敗: {str(e)}")
        data['sentiment'] = {'overall_score': 0, 'bullish_ratio': 0}

    # 數據品質驗證
    checker = DataQualityChecker()
    quality_score, checks = checker.validate(data['market'], SYMBOLS.get(mode, []))
    data['quality'] = {'score': quality_score, 'checks': checks}

    logger.info(f"{mode} 數據收集完成: {len(data['market'])} 個標的, {len(data['news'])} 則新聞, 品質分數: {quality_score}")
    return data
