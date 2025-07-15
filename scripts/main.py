import yfinance as yf
import json
import os
import logging
from datetime import datetime
from gtts import gTTS
import random
import subprocess
import requests
from openai import OpenAI
from dotenv import load_dotenv

try:
    from feedgen.feed import FeedGenerator
except ImportError as e:
    logging.error(f"Failed to import feedgen: {e}")
    exit(1)

# Setup logging
def setup_logger():
    os.makedirs("data/logs", exist_ok=True)
    log_file = f"data/logs/podcast_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()
logger.info("Logger initialized")

# Ensure directories
def ensure_directories():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    logger.info("Ensured directories")

# Load environment variables
load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")
if not XAI_API_KEY:
    logger.error("XAI_API_KEY not set in environment variables")
    exit(1)

# Initialize Grok API client
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1"
)

# Fetch financial data
def fetch_financial_data():
    logger.info("Fetching financial data")
    tickers = {
        'indices': ['^DJI', '^IXIC', '^GSPC', '^SOX'],
        'etfs': ['QQQ', 'SPY', 'IBIT'],
        'crypto_commodities': ['BTC-USD', 'GC=F'],
        'treasury': ['^TNX']
    }
    data = {'indices': {}, 'etfs': {}, 'crypto_commodities': {}, 'treasury': {}}
    
    for category, symbols in tickers.items():
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period='2d')
                if len(hist) < 2:
                    logger.error(f"Insufficient data for {sym}")
                    return None
                close = hist['Close'][-1]
                prev_close = hist['Close'][-2]
                change = ((close - prev_close) / prev_close) * 100
                data[category][sym] = {'close': round(close, 2), 'change': round(change, 2)}
                logger.info(f"Fetched {sym}: close={close}, change={change}%")
            except Exception as e:
                logger.error(f"Error fetching {sym}: {e}")
                return None
    
    trending_stocks = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
    data['trending_stocks'] = {}
    for stock in trending_stocks:
        try:
            ticker = yf.Ticker(stock)
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                logger.error(f"Insufficient data for {stock}")
                return None
            close = hist['Close'][-1]
            prev_close = hist['Close'][-2]
            change = ((close - prev_close) / prev_close) * 100
            data['trending_stocks'][stock] = {'close': round(close, 2), 'change': round(change, 2)}
            logger.info(f"Fetched trending stock {stock}: close={close}, change={change}%")
        except Exception as e:
            logger.error(f"Error fetching {stock}: {e}")
            return None
    
    indices_avg_change = sum(data['indices'][idx]['change'] for idx in data['indices']) / len(data['indices'])
    data['fund_flow'] = "資金流入" if indices_avg_change > 0 else "資金流出"
    logger.info(f"Fund flow: {data['fund_flow']}")
    
    return data

# Fetch AI news
def fetch_ai_news():
    logger.info("Fetching AI news")
    try:
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            logger.warning("NEWSAPI_KEY not set, falling back to default")
            return "今天沒有特別的 AI 新聞，但 AI 持續改變世界！"
        url = f"https://newsapi.org/v2/top-headlines?category=technology&q=AI&language=en&apiKey={api_key}"
        response = requests.get(url, timeout=10)
        articles = response.json().get('articles', [])
        if articles:
            news = articles[0]['title'] + " - " + articles[0]['description'][:100] + "..."
            logger.info(f"AI news fetched: {news}")
            return news
        logger.warning("No AI news found")
        return "今天沒有特別的 AI 新聞，但 AI 持續改變世界！"
    except Exception as e:
        logger.error(f"Error fetching AI news: {e}")
        return "今天沒有特別的 AI 新聞，但 AI 持續改變世界！"

# Fetch economic news
def fetch_economic_news():
    logger.info("Fetching economic news")
    try:
        api_key = os.getenv("NEWSAPI_KEY")
        if not api_key:
            logger.warning("NEWSAPI_KEY not set, falling back to default")
            return "今天沒有特別的經濟新聞，市場穩穩走！"
        url = f"https://newsapi.org/v2/top-headlines?category=business&country=us&apiKey={api_key}"
        response = requests.get(url, timeout=10)
        articles = response.json().get('articles', [])
        if articles:
            news = articles[0]['title'] + " - " + articles[0]['description'][:100] + "..."
            logger.info(f"Economic news fetched: {news}")
            return news
        logger.warning("No economic news found")
        return "今天沒有特別的經濟新聞，市場穩穩走！"
    except Exception as e:
        logger.error(f"Error fetching economic news: {e}")
        return "今天沒有特別的經濟新聞，市場穩穩走！"

# Generate podcast script using Grok API
def generate_script():
    logger.info("Starting script generation with Grok API")
    ensure_directories()
    try:
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            phrases = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load tw_phrases.json: {e}")
        return None
    
    data = fetch_financial_data() or {
        'indices': {
            '^DJI': {'close': 44371.51, 'change': -0.63},
            '^IXIC': {'close': 20585.53, 'change': -0.22},
            '^GSPC': {'close': 6259.75, 'change': -0.33},
            '^SOX': {'close': 5696.29, 'change': -0.21}
        },
        'etfs': {
            'QQQ': {'close': 500.12, 'change': -0.15},
            'SPY': {'close': 600.45, 'change': -0.25},
            'IBIT': {'close': 40.78, 'change': 1.20}
        },
        'crypto_commodities': {
            'BTC-USD': {'close': 65000.00, 'change': 2.50},
            'GC=F': {'close': 2400.00, 'change': -0.50}
        },
        'treasury': {
            '^TNX': {'close': 4.20, 'change': 0.10}
        },
        'trending_stocks': {
            'AAPL': {'close': 230.54, 'change': 0.45},
            'MSFT': {'close': 420.72, 'change': -0.30},
            'NVDA': {'close': 135.58, 'change': 1.20},
            'TSLA': {'close': 250.00, 'change': -0.80},
            'GOOGL': {'close': 180.34, 'change': 0.25}
        },
        'fund_flow': '資金流出'
    }
    
    ai_news = fetch_ai_news()
    economic_news = fetch_economic_news()
    date = datetime.now().strftime('%Y年%m月%d日')
    
    prompt = f"""
你是一位親切、風趣的台灣中年大叔，主持《大叔說財經科技投資》播客，語氣自然、像在跟朋友聊天，使用台灣慣用語。請根據以下數據和要求，生成一篇約 400-500 字的逐字稿，內容每天不同，涵蓋以下七部分，語氣參考以下例句：

例句參考：
{json.dumps(phrases, ensure_ascii=False)}

數據：
1. 美股四大指數：
- 道瓊 (^DJI): {data['indices']['^DJI']['close']} 點，{'漲' if data['indices']['^DJI']['change'] >= 0 else '跌'} {abs(data['indices']['^DJI']['change'])}%
- 納斯達克 (^IXIC): {data['indices']['^IXIC']['close']} 點，{'漲' if data['indices']['^IXIC']['change'] >= 0 else '跌'} {abs(data['indices']['^IXIC']['change'])}%
- 標普500 (^GSPC): {data['indices']['^GSPC']['close']} 點，{'漲' if data['indices']['^GSPC']['change'] >= 0 else '跌'} {abs(data['indices']['^GSPC']['change'])}%
- 費城半導體 (^SOX): {data['indices']['^SOX']['close']} 點，{'漲' if data['indices']['^SOX']['change'] >= 0 else '跌'} {abs(data['indices']['^SOX']['change'])}%

2. ETF：
- QQQ: {data['etfs']['QQQ']['close']} 點，{'漲' if data['etfs']['QQQ']['change'] >= 0 else '跌'} {abs(data['etfs']['QQQ']['change'])}%
- SPY: {data['etfs']['SPY']['close']} 點，{'漲' if data['etfs']['SPY']['change'] >= 0 else '跌'} {abs(data['etfs']['SPY']['change'])}%
- IBIT: {data['etfs']['IBIT']['close']} 點，{'漲' if data['etfs']['IBIT']['change'] >= 0 else '跌'} {abs(data['etfs']['IBIT']['change'])}%

3. 比特幣與黃金：
- 比特幣 (BTC-USD): {data['crypto_commodities']['BTC-USD']['close']} 美元，{'漲' if data['crypto_commodities']['BTC-USD']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['BTC-USD']['change'])}%
- 黃金期貨 (GC=F): {data['crypto_commodities']['GC=F']['close']} 美元，{'漲' if data['crypto_commodities']['GC=F']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['GC=F']['change'])}%
- 十年期國債殖利率 (^TNX): {data['treasury']['^TNX']['close']}%，{'上升' if data['treasury']['^TNX']['change'] >= 0 else '下降'} {abs(data['treasury']['^TNX']['change'])}%

4. 熱門美股：
- 蘋果 (AAPL): {data['trending_stocks']['AAPL']['close']} 美元，{'漲' if data['trending_stocks']['AAPL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['AAPL']['change'])}%
- 微軟 (MSFT): {data['trending_stocks']['MSFT']['close']} 美元，{'漲' if data['trending_stocks']['MSFT']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['MSFT']['change'])}%
- 輝達 (NVDA): {data['trending_stocks']['NVDA']['close']} 美元，{'漲' if data['trending_stocks']['NVDA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['NVDA']['change'])}%
- 特斯拉 (TSLA): {data['trending_stocks']['TSLA']['close']} 美元，{'漲' if data['trending_stocks']['TSLA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['TSLA']['change'])}%
- 谷歌 (GOOGL): {data['trending_stocks']['GOOGL']['close']} 美元，{'漲' if data['trending_stocks']['GOOGL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['GOOGL']['change'])}%
- 總體資金流向：{data['fund_flow']}

5. AI 新聞：{ai_news}
6. 經濟新聞：{economic_news}
7. 投資金句：從例句中隨機選一句

要求：
- 語氣親切、風趣，像台灣中年大叔跟朋友聊天。
- 使用繁體中文，融入台灣慣用語。
- 腳本分七部分，標題清晰（如「美股四大指數」、「熱門美股」）。
- 每部分簡短分析，融入例句中的語氣（正向/負向）。
- 總長約 400-500 字，適合 15 分鐘語音。
- 開頭包含日期（{date}），結尾以例句中的 closing 結束。
"""
    
    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "你是一位親切、風趣的台灣中年大叔，主持《大叔說財經科技投資》播客，語氣自然、像在跟朋友聊天，使用繁體中文和台灣慣用語。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        script = response.choices[0].message.content
        with open('data/script.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Script generated successfully
