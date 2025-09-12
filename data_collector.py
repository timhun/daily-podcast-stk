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

    def fetch_market_data(self, symbol, timeframe='daily'):
    try:
        ticker = yf.Ticker(symbol)
        period = '1y' if timeframe == 'daily' else '14d'
        interval = '1d' if timeframe == 'daily' else '1h'
        data = ticker.history(period=period, interval=interval, auto_adjust=True)
        if data.empty:
            logger.error(f"{symbol} {timeframe} 數據為空")
            return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
        data = data.reset_index()
        # 檢查 Date 欄位
        if 'Date' not in data.columns:
            logger.warning(f"{symbol} {timeframe} 缺少 'Date' 欄位，使用索引")
            data['date'] = pd.to_datetime(data.index, utc=True)
        else:
            data['date'] = pd.to_datetime(data['Date'], utc=True)
        data['symbol'] = symbol
        data['change'] = data['Close'].pct_change()
        data = data[['date', 'symbol', 'Open', 'High', 'Low', 'Close', 'change', 'Volume']]
        data.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume']
        if not all(col in data.columns for col in ['open', 'close', 'volume']):
            logger.error(f"{symbol} {timeframe} 數據缺少必要欄位: {list(data.columns)}")
            return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
        logger.info(f"{symbol} {timeframe} 數據獲取成功: {len(data)} 行")
        return data
    except Exception as e:
        logger.error(f"{symbol} {timeframe} 數據獲取失敗: {str(e)}")
        return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'change', 'volume'])
    
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
