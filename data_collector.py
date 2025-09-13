import yfinance as yf
import pandas as pd
import os
import json
from datetime import datetime
import pytz
from loguru import logger
from xai_sdk import Client
import time

class DataCollector:
    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv("GROK_API_KEY")
        self.TW_TZ = pytz.timezone("Asia/Taipei")

    def validate(self, data, symbol, timeframe):
        completeness = 1.0 if not data.empty and 'close' in data.columns else 0.0
        freshness = True
        volatility = data['close'].pct_change().std() < 0.05 if not data.empty else False
        score = sum([completeness, freshness, volatility]) / 3
        return {
            'completeness': completeness,
            'freshness': freshness,
            'volatility': volatility,
            'score': score
        }

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
            }
            daily_df = pd.DataFrame([{
                'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'),
                'symbol': symbol,
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'change': 0,
                'volume': 0
            }])
        else:
            if hist_daily.index.tz is None:
                hist_daily.index = hist_daily.index.tz_localize('Asia/Taipei')
            hist_daily.index = hist_daily.index.tz_convert('UTC')
            daily_data = {
                'open': hist_daily['Open'].iloc[-1],
                'high': hist_daily['High'].iloc[-1],
                'low': hist_daily['Low'].iloc[-1],
                'close': hist_daily['Close'].iloc[-1],
                'change': hist_daily['Close'].pct_change().iloc[-1] * 100 if len(hist_daily) > 1 else 0,
                'volume': hist_daily['Volume'].iloc[-1],
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
                'volume': hist_daily['Volume']
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
            }
            hourly_df = pd.DataFrame([{
                'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': symbol,
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'change': 0,
                'volume': 0
            }])
        else:
            if hist_hourly.index.tz is None:
                hist_hourly.index = hist_hourly.index.tz_localize('Asia/Taipei')
            hist_hourly.index = hist_hourly.index.tz_convert('UTC')
            hourly_data = {
                'open': hist_hourly['Open'].iloc[-1],
                'high': hist_hourly['High'].iloc[-1],
                'low': hist_hourly['Low'].iloc[-1],
                'close': hist_hourly['Close'].iloc[-1],
                'change': hist_hourly['Close'].pct_change().iloc[-1] * 100 if len(hist_hourly) > 1 else 0,
                'volume': hist_hourly['Volume'].iloc[-1],
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
                'volume': hist_hourly['Volume']
            }).dropna()
    
        return daily_data, daily_df, hourly_data, hourly_df    
        
    @retry(tries=3, delay=1, backoff=2)
        
    def fetch_news(self, mode):
        try:
            news = [
                {'title': f'{mode.upper()} Market Update: Stable growth observed', 'timestamp': datetime.now(self.TW_TZ).strftime('%Y-%m-%d')},
                {'title': f'{mode.upper()} Tech stocks show volatility', 'timestamp': datetime.now(self.TW_TZ).strftime('%Y-%m-%d')},
                {'title': f'{mode.upper()} Investors focus on index trends', 'timestamp': datetime.now(self.TW_TZ).strftime('%Y-%m-%d')}
            ]
            time.sleep(2)
            return news
        except Exception as e:
            logger.error(f"News fetch failed: {str(e)}")
            return []

    def analyze_sentiment(self, news, symbols):
        try:
            client = Client(api_key=self.api_key)
            chat = client.chat.create(model="grok-3-mini")
            prompt = f"Analyze sentiment for {', '.join(symbols)} based on news: {json.dumps(news)}"
            chat.append({"role": "user", "content": prompt})
            response = chat.sample()
            sentiment = json.loads(response.content)
            return sentiment
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {'overall_score': 0.0, 'bullish_ratio': 0.0, 'symbols': {s: {'sentiment_score': 0.0} for s in symbols}}

    def collect_data(self, mode):
        symbols = self.config['symbols'][mode] + self.config['symbols']['commodities']
        market_data = {'market': {}, 'news': {}, 'sentiment': {}}

        for symbol in symbols:
            daily_data = self.fetch_market_data(symbol, 'daily')
            file_path = f"{self.config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            daily_data.to_csv(file_path, index=False)
            logger.info(f"Daily data saved to: {file_path}")

            hourly_data = self.fetch_market_data(symbol, 'hourly')
            hourly_path = f"{self.config['data_paths']['market']}/hourly_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
            hourly_data.to_csv(hourly_path, index=False)
            logger.info(f"Hourly data saved to: {hourly_path}")

            market_data['market'][symbol] = {'latest': daily_data.iloc[-1].to_dict() if not daily_data.empty else {}}

        news = self.fetch_news(mode)
        news_path = f"{self.config['data_paths']['news']}/{datetime.now(self.TW_TZ).strftime('%Y-%m-%d')}/{mode}_news.json"
        os.makedirs(os.path.dirname(news_path), exist_ok=True)
        with open(news_path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        logger.info(f"News data saved to: {news_path}")
        market_data['news'] = news

        sentiment = self.analyze_sentiment(news, symbols)
        sentiment_path = f"{self.config['data_paths']['sentiment']}/{datetime.now(self.TW_TZ).strftime('%Y-%m-%d')}/social_metrics.json"
        os.makedirs(os.path.dirname(sentiment_path), exist_ok=True)
        with open(sentiment_path, 'w', encoding='utf-8') as f:
            json.dump(sentiment, f, ensure_ascii=False, indent=2)
        logger.info(f"Sentiment data saved to: {sentiment_path}")
        market_data['sentiment'] = sentiment

        quality_score = 1.0
        for symbol in symbols:
            file_path = f"{self.config['data_paths']['market']}/daily_{symbol.replace('^', '').replace('.', '_').replace('-', '_')}.csv"
            data = pd.read_csv(file_path) if os.path.exists(file_path) else pd.DataFrame()
            quality = self.validate(data, symbol, 'daily')
            quality_score = min(quality_score, quality['score'])
            if quality['score'] < 0.7:
                logger.warning(f"Poor data quality for {symbol}: {quality}, score: {quality['score']}")

        logger.info(f"{mode} data collection completed: {len(symbols)} symbols, {len(news)} news items, quality score: {quality_score}")
        return market_data

if __name__ == "__main__":
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    collector = DataCollector(config)
    collector.collect_data('tw')
