import yfinance as yf
import requests
from bs4 import BeautifulSoup
import os
import re
import json
import datetime
from loguru import logger
from retry import retry
from transformers import pipeline
import pandas as pd
import httpx
from config import get_market_data_path

# Load config.json
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Setup logging
logger.add("logs/data_collector.log", rotation="1 MB")

SYMBOLS = config["symbols"]
NEWS_SOURCES = config["news_sources"]

# ─────────────────────────────────────────────
# FinBERT Multi-Layer Fallback System
# ─────────────────────────────────────────────
_sentiment_analyzer = None   # lazy-loaded
_finbert_layer = 0            # 0=unloaded, 1=ProsusAI, 2=yiyanghkust, 3=gemini/keyword

def get_sentiment_analyzer():
    """
    Attempt to load FinBERT models in order; fallback to None (keyword-based).
    Layer 1: ProsusAI/finbert  --- most common
    Layer 2: yiyanghkust/finbert-pretrain
    Layer 3: Gemini API (optional)
    Layer 4: keyword (always available)
    """
    global _sentiment_analyzer, _finbert_layer
    if _sentiment_analyzer is not None:
        return _sentiment_analyzer, _finbert_layer

    # Try HuggingFace FinBERT models
    for layer_id, model_name in enumerate(
        ["ProsusAI/finbert", "yiyanghkust/finbert-pretrain"], start=1
    ):
        try:
            _sentiment_analyzer = pipeline("sentiment-analysis", model=model_name, device=-1)
            _finbert_layer = layer_id
            logger.info(f"FinBERT loaded: {model_name}")
            return _sentiment_analyzer, _finbert_layer
        except Exception as e:
            logger.warning(f"FinBERT Layer {layer_id} ({model_name}) failed: {e}")

    logger.warning("HuggingFace FinBERT unavailable; using keyword fallback")
    _finbert_layer = 3  # Gemini / keyword fallback
    _sentiment_analyzer = None
    return None, _finbert_layer


def keyword_sentiment(text):
    """Keyword-based sentiment — always available, no external dependencies."""
    bullish = ["牛市","多頭","買進","Buy","看好","漲","利多","成長","突破","創新高","盈利","反彈","超賣"]
    bearish = ["熊市","空頭","賣出","Sell","看淡","跌","利空","衰退","跌破","新低","虧損","崩盤","超買"]
    b = sum(1 for kw in bullish if kw in text)
    r = sum(1 for kw in bearish if kw in text)
    if b > r:
        return {"label": "positive", "score": min(0.9, 0.55 + b * 0.05)}
    elif r > b:
        return {"label": "negative", "score": min(0.9, 0.55 + r * 0.05)}
    return {"label": "neutral", "score": 0.5}


def analyze_sentiments(texts, analyzer):
    """
    Unified sentiment analysis.
    - analyzer is not None → Use FinBERT (HuggingFace transformers)
    - analyzer is None → Use keyword fallback
    """
    if not texts:
        return []
    if analyzer is not None:
        return analyzer(texts)
    # Keyword fallback
    return [keyword_sentiment(t) for t in texts]


# ─────────────────────────────────────────────
# DataQualityChecker
# ─────────────────────────────────────────────
class DataQualityChecker:
    def __init__(self):
        self.quality_thresholds = config["quality_thresholds"]

    def check_completeness(self, data, expected_keys):
        total = len(expected_keys)
        present = sum(1 for key in expected_keys if key in data and data[key])
        return present / total if total > 0 else 0

    def check_freshness(self, data_timestamp):
        now = datetime.datetime.now(datetime.timezone.utc)
        age_hours = (now - data_timestamp).total_seconds() / 3600
        return age_hours <= self.quality_thresholds["freshness_hours"]

    def check_volatility(self, data, symbol):
        change = abs(data.get(symbol, {}).get("change", 0))
        return change <= self.quality_thresholds["volatility_threshold"] * 100

    def validate(self, data, symbols):
        checks = {
            "completeness": self.check_completeness(data, symbols),
            "freshness": self.check_freshness(datetime.datetime.now(datetime.timezone.utc)),
            "volatility": all(self.check_volatility(data, symbol) for symbol in symbols),
        }
        quality_score = sum(checks.values()) / len(checks)
        if quality_score < 0.8:
            logger.warning(f"數據品質不佳: {checks}, 分數: {quality_score}")
        return quality_score, checks


# ─────────────────────────────────────────────
# Data Fetching
# ─────────────────────────────────────────────
@retry(tries=3, delay=1, backoff=2)
def fetch_market_data(symbol, period="1y"):
    ticker = yf.Ticker(symbol)
    hist_daily = ticker.history(period=period)
    if hist_daily.empty:
        logger.error(f"{symbol} daily data empty")
        daily_data = {"open": 0, "high": 0, "low": 0, "close": 0, "change": 0, "volume": 0, "timestamp": datetime.datetime.now(datetime.timezone.utc)}
        daily_df = pd.DataFrame([{"date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"), "symbol": symbol, "open": 0, "high": 0, "low": 0, "close": 0, "change": 0, "volume": 0}])
    else:
        if hist_daily.index.tz is None:
            hist_daily.index = hist_daily.index.tz_localize("Asia/Taipei")
        hist_daily.index = hist_daily.index.tz_convert("UTC")
        daily_data = {"open": hist_daily["Open"].iloc[-1], "high": hist_daily["High"].iloc[-1], "low": hist_daily["Low"].iloc[-1], "close": hist_daily["Close"].iloc[-1], "change": hist_daily["Close"].pct_change().iloc[-1] * 100 if len(hist_daily) > 1 else 0, "volume": hist_daily["Volume"].iloc[-1], "timestamp": hist_daily.index[-1]}
        daily_df = pd.DataFrame({"date": hist_daily.index.strftime("%Y-%m-%d"), "symbol": symbol, "open": hist_daily["Open"], "high": hist_daily["High"], "low": hist_daily["Low"], "close": hist_daily["Close"], "change": hist_daily["Close"].pct_change() * 100, "volume": hist_daily["Volume"]}).dropna()

    hist_hourly = ticker.history(period="14d", interval="1h")
    if hist_hourly.empty:
        hourly_data = {"open": 0, "high": 0, "low": 0, "close": 0, "change": 0, "volume": 0, "timestamp": datetime.datetime.now(datetime.timezone.utc)}
        hourly_df = pd.DataFrame([{"date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "symbol": symbol, "open": 0, "high": 0, "low": 0, "close": 0, "change": 0, "volume": 0}])
    else:
        if hist_hourly.index.tz is None:
            hist_hourly.index = hist_hourly.index.tz_localize("Asia/Taipei")
        hist_hourly.index = hist_hourly.index.tz_convert("UTC")
        hourly_data = {"open": hist_hourly["Open"].iloc[-1], "high": hist_hourly["High"].iloc[-1], "low": hist_hourly["Low"].iloc[-1], "close": hist_hourly["Close"].iloc[-1], "change": hist_hourly["Close"].pct_change().iloc[-1] * 100 if len(hist_hourly) > 1 else 0, "volume": hist_hourly["Volume"].iloc[-1], "timestamp": hist_hourly.index[-1]}
        hourly_df = pd.DataFrame({"date": hist_hourly.index.strftime("%Y-%m-%d %H:%M:%S"), "symbol": symbol, "open": hist_hourly["Open"], "high": hist_hourly["High"], "low": hist_hourly["Low"], "close": hist_hourly["Close"], "change": hist_hourly["Close"].pct_change() * 100, "volume": hist_hourly["Volume"]}).dropna()

    return daily_data, daily_df, hourly_data, hourly_df


@retry(tries=3, delay=1, backoff=2)
def fetch_news(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item", limit=3)
        return [{"title": item.title.text, "description": item.description.text} for item in items if item.title and item.description]
    except Exception as e:
        logger.error(f"抓取新聞 {url} 失敗: {str(e)}")
        return []


# ─────────────────────────────────────────────
# Main: collect_data
# ─────────────────────────────────────────────
def collect_data(mode):
    data = {"market": {}, "news": [], "sentiment": {}}
    today = datetime.date.today().strftime("%Y-%m-%d")
    output_dir = f"data/news/{today}"
    market_dir = "data/market"
    os.makedirs(market_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Fetch market data
    for symbol in SYMBOLS.get(mode, []):
        try:
            daily_data, daily_df, hourly_data, hourly_df = fetch_market_data(symbol)
            data["market"][symbol] = daily_data
            daily_file = get_market_data_path(symbol, "daily")
            daily_df.to_csv(daily_file, index=False)
            logger.info(f"每日數據儲存至: {daily_file}")
            hourly_file = get_market_data_path(symbol, "hourly")
            hourly_df.to_csv(hourly_file, index=False)
            logger.info(f"每小時數據儲存至: {hourly_file}")
        except Exception as e:
            logger.error(f"抓取 {symbol} 市場數據失敗: {str(e)}")
            data["market"][symbol] = {"close": 0, "change": 0}

    # Fetch news
    news_by_symbol = {symbol: [] for symbol in SYMBOLS.get(mode, [])}
    for url in NEWS_SOURCES.get(mode, []):
        news_items = fetch_news(url)
        for item in news_items:
            for symbol in SYMBOLS.get(mode, []):
                if symbol in item["title"] or symbol in item["description"]:
                    news_by_symbol[symbol].append(item)
        data["news"].extend(news_items)

    # Save news
    news_path = f"{output_dir}/{mode}_news.json"
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(data["news"], f, ensure_ascii=False, indent=2)
    logger.info(f"新聞數據儲存至: {news_path}")

    # ── Multi-Layer Sentiment Analysis ──
    try:
        # Layer 1-2: Try HuggingFace FinBERT; Layer 3-4: keyword fallback
        sentiment_analyzer, finbert_layer = get_sentiment_analyzer()
        logger.info(f"Sentiment Layer: {finbert_layer}")

        headlines = [item["title"] for item in data["news"]]
        sentiments = analyze_sentiments(headlines, sentiment_analyzer)
        overall_score = 0.0
        bullish_ratio = 0.5
        if sentiments:
            overall_score = sum(s["score"] if s["label"] == "positive" else -s["score"] for s in sentiments) / len(sentiments)
            bullish_ratio = sum(1 for s in sentiments if s["label"] == "positive") / len(sentiments)

        sentiment_data = {
            "overall_score": overall_score,
            "bullish_ratio": bullish_ratio,
            "layer": finbert_layer,
            "symbols": {},
        }
        for symbol in SYMBOLS.get(mode, []):
            symbol_headlines = [item["title"] for item in news_by_symbol[symbol]]
            if symbol_headlines:
                symbol_sentiments = analyze_sentiments(symbol_headlines, sentiment_analyzer)
                symbol_score = sum(s["score"] if s["label"] == "positive" else -s["score"] for s in symbol_sentiments) / len(symbol_sentiments) if symbol_sentiments else 0.0
            else:
                symbol_score = 0.0
            sentiment_data["symbols"][symbol] = {"sentiment_score": symbol_score}

        data["sentiment"] = sentiment_data
        sentiment_path = f"data/sentiment/{today}/social_metrics.json"
        os.makedirs(os.path.dirname(sentiment_path), exist_ok=True)
        with open(sentiment_path, "w", encoding="utf-8") as f:
            json.dump(sentiment_data, f, ensure_ascii=False, indent=2)
        logger.info(f"情緒數據儲存至: {sentiment_path}")

    except Exception as e:
        logger.error(f"情緒分析失敗: {str(e)} — 使用中性預設值")
        data["sentiment"] = {
            "overall_score": 0,
            "bullish_ratio": 0.5,
            "layer": "error",
            "symbols": {symbol: {"sentiment_score": 0.0} for symbol in SYMBOLS.get(mode, [])},
        }

    # Quality check
    checker = DataQualityChecker()
    quality_score, checks = checker.validate(data["market"], SYMBOLS.get(mode, []))
    data["quality"] = {"score": quality_score, "checks": checks}

    logger.info(f"{mode} 數據收集完成: {len(data['market'])} 個標的, {len(data['news'])} 則新聞, 品質分數: {quality_score}")
    return data
