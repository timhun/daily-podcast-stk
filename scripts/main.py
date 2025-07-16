import yfinance as yf
import json
import os
import logging
from datetime import datetime
from gtts import gTTS
import random
import subprocess
import requests

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

# Fetch financial data
def fetch_financial_data():
    logger.info("Fetching financial data")
    tickers = {
        'indices': ['^DJI', '^IXIC', '^GSPC', '^SOX'],
        'etfs': ['QQQ', 'SPY', 'IBIT'],
        'crypto_commodities': ['BTC-USD', 'GC=F'],  # Bitcoin, Gold Futures
        'treasury': ['^TNX']  # 10-Year Treasury Yield
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
    
    # Fetch top 5 trending stocks (simulated with fixed stocks for simplicity)
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
    
    # Simulate fund flow (direction based on indices' average change)
    indices_avg_change = sum(data['indices'][idx]['change'] for idx in data['indices']) / len(data['indices'])
    data['fund_flow'] = "資金流入" if indices_avg_change > 0 else "資金流出"
    logger.info(f"Fund flow: {data['fund_flow']}")
    
    return data

# Fetch AI news (using NewsAPI as example)
def fetch_ai_news():
    logger.info("Fetching AI news")
    try:
        api_key = "YOUR_NEWSAPI_KEY"  # 需替換為您的 NewsAPI 密鑰
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
        api_key = "YOUR_NEWSAPI_KEY"  # 需替換為您的 NewsAPI 密鑰
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

# Generate podcast script
def generate_script():
    logger.info("Starting script generation")
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
    
    date = datetime.now().strftime('%Y年%m月%d日')
    analysis = lambda x: random.choice(phrases['analysis_positive'] if x >= 0 else phrases['analysis_negative'])
    
    script = (
        f"{random.choice(phrases['greetings'])}今天是{date}，大叔帶你看財經市場的最新動態！\n\n"
        
        f"### 1. 美股四大指數\n"
        f"先來看美股四大指數的表現：\n"
        f"- 道瓊指數收在 {data['indices']['^DJI']['close']} 點，{'漲' if data['indices']['^DJI']['change'] >= 0 else '跌'} {abs(data['indices']['^DJI']['change'])}%，{analysis(data['indices']['^DJI']['change'])}\n"
        f"- 納斯達克收在 {data['indices']['^IXIC']['close']} 點，{'漲' if data['indices']['^IXIC']['change'] >= 0 else '跌'} {abs(data['indices']['^IXIC']['change'])}%，{analysis(data['indices']['^IXIC']['change'])}\n"
        f"- 標普500收在 {data['indices']['^GSPC']['close']} 點，{'漲' if data['indices']['^GSPC']['change'] >= 0 else '跌'} {abs(data['indices']['^GSPC']['change'])}%，{analysis(data['indices']['^GSPC']['change'])}\n"
        f"- 費城半導體收在 {data['indices']['^SOX']['close']} 點，{'漲' if data['indices']['^SOX']['change'] >= 0 else '跌'} {abs(data['indices']['^SOX']['change'])}%，{analysis(data['indices']['^SOX']['change'])}\n\n"
        
        f"### 2. ETF 動態\n"
        f"再來看看熱門 ETF：\n"
        f"- QQQ（科技股 ETF）收在 {data['etfs']['QQQ']['close']} 點，{'漲' if data['etfs']['QQQ']['change'] >= 0 else '跌'} {abs(data['etfs']['QQQ']['change'])}%，科技股{'穩定' if abs(data['etfs']['QQQ']['change']) < 1 else '波動較大'}。\n"
        f"- SPY（標普500 ETF）收在 {data['etfs']['SPY']['close']} 點，{'漲' if data['etfs']['SPY']['change'] >= 0 else '跌'} {abs(data['etfs']['SPY']['change'])}%，市場整體{'平穩' if abs(data['etfs']['SPY']['change']) < 1 else '有點震盪'}。\n"
        f"- IBIT（比特幣 ETF）收在 {data['etfs']['IBIT']['close']} 點，{'漲' if data['etfs']['IBIT']['change'] >= 0 else '跌'} {abs(data['etfs']['IBIT']['change'])}%，加密貨幣市場{'火熱' if data['etfs']['IBIT']['change'] > 1 else '趨於冷靜'}。\n\n"
        
        f"### 3. 比特幣與黃金\n"
        f"加密貨幣和商品市場：\n"
        f"- 比特幣（BTC-USD）報價 {data['crypto_commodities']['BTC-USD']['close']} 美元，{'漲' if data['crypto_commodities']['BTC-USD']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['BTC-USD']['change'])}%，{'市場熱度高' if data['crypto_commodities']['BTC-USD']['change'] > 1 else '穩中求進'}。\n"
        f"- 黃金期貨（GC=F）報價 {data['crypto_commodities']['GC=F']['close']} 美元，{'漲' if data['crypto_commodities']['GC=F']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['GC=F']['change'])}%，{'避險需求強' if data['crypto_commodities']['GC=F']['change'] > 0 else '市場偏向風險資產'}。\n"
        f"- 十年期美國國債殖利率 {data['treasury']['^TNX']['close']}%，{'上升' if data['treasury']['^TNX']['change'] >= 0 else '下降'} {abs(data['treasury']['^TNX']['change'])}%，影響市場預期。\n\n"
        
        f"### 4. 熱門美股\n"
        f"看看 Top 5 熱門美股：\n"
        f"- 蘋果（AAPL）收在 {data['trending_stocks']['AAPL']['close']} 美元，{'漲' if data['trending_stocks']['AAPL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['AAPL']['change'])}%，{analysis(data['trending_stocks']['AAPL']['change'])}\n"
        f"- 微軟（MSFT）收在 {data['trending_stocks']['MSFT']['close']} 美元，{'漲' if data['trending_stocks']['MSFT']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['MSFT']['change'])}%，{analysis(data['trending_stocks']['MSFT']['change'])}\n"
        f"- 輝達（NVDA）收在 {data['trending_stocks']['NVDA']['close']} 美元，{'漲' if data['trending_stocks']['NVDA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['NVDA']['change'])}%，{analysis(data['trending_stocks']['NVDA']['change'])}\n"
        f"- 特斯拉（TSLA）收在 {data['trending_stocks']['TSLA']['close']} 美元，{'漲' if data['trending_stocks']['TSLA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['TSLA']['change'])}%，{analysis(data['trending_stocks']['TSLA']['change'])}\n"
        f"- 谷歌（GOOGL）收在 {data['trending_stocks']['GOOGL']['close']} 美元，{'漲' if data['trending_stocks']['GOOGL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['GOOGL']['change'])}%，{analysis(data['trending_stocks']['GOOGL']['change'])}\n"
        f"總體來看，市場資金目前傾向{data['fund_flow']}，投資人需謹慎觀察！\n\n"
        
        f"### 5. AI 新聞\n"
        f"{random.choice(phrases['news_intro'])}\n{fetch_ai_news()}\n\n"
        
        f"### 6. 經濟新聞\n"
        f"{random.choice(phrases['news_intro'])}\n{fetch_economic_news()}\n\n"
        
        f"### 7. 今日投資金句\n"
        f"{random.choice(phrases['investment_quotes'])}\n\n"
        
        f"{random.choice(phrases['closing'])}"
    )
    
    try:
        with open('data/script.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Script generated successfully")
        return script
    except Exception as e:
        logger.error(f"Failed to write script: {e}")
        return None

# Text to audio
def text_to_audio(script):
    logger.info("Starting text-to-audio conversion")
    date = datetime.now().strftime('%Y%m%d')
    output_file = f"audio/episode_{date}.mp3"
    temp_file = "audio/temp.mp3"
    
    try:
        ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if ffmpeg_check.returncode != 0:
            logger.error(f"FFmpeg not installed: {ffmpeg_check.stderr}")
            return None
        logger.info(f"FFmpeg version: {ffmpeg_check.stdout.splitlines()[0]}")
        
        logger.info("Generating audio with gTTS")
        tts = gTTS(text=script, lang='zh-tw', slow=False)
        tts.save(temp_file)
        if not os.path.exists(temp_file):
            logger.error(f"Temporary audio file not created: {temp_file}")
            return None
        logger.info(f"Temporary audio file created: {temp_file}")
        
        logger.info(f"Processing audio to {output_file}")
        result = subprocess.run(
            ['ffmpeg', '-i', temp_file, '-filter:a', 'atempo=1.3', '-y', output_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg processing failed: {result.stderr}")
            return None
        
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info(f"Removed temporary file: {temp_file}")
        
        if not os.path.exists(output_file):
            logger.error(f"Output audio file not created: {output_file}")
            return None
        logger.info(f"Audio generated successfully: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")
        return None

# Generate RSS feed
def generate_rss(audio_file):
    logger.info("Starting RSS generation")
    try:
        fg = FeedGenerator()
        fg.title('大叔說財經科技投資')
        fg.author({'name': '大叔'})
        fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
        fg.description('每日美股、ETF、比特幣、AI與經濟新聞，用台灣味聊投資')
        fg.language('zh-tw')
        fg.itunes_type('serial')
        
        date = datetime.now().strftime('%Y%m%d')
        fe = fg.add_entry()
        fe.title(f'美股與科技播報 - {date}')
        fe.description('大叔帶你看美股、ETF、比特幣與最新財經動態！')
        fe.enclosure(url=f'https://timhun.github.io/daily-podcast-stk/audio/episode_{date}.mp3', type='audio/mpeg', length='45000000')
        fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
        fe.itunes_order(str(int(date)))
        
        fg.rss_file('feed.xml')
        logger.info("RSS feed updated successfully")
        return True
    except Exception as e:
        logger.error(f"RSS generation failed: {e}")
        return None

# Main execution
if __name__ == "__main__":
    logger.info("Starting podcast generation")
    try:
        script = generate_script()
        if not script:
            logger.error("Script generation failed, aborting")
            exit(1)
        
        audio_file = text_to_audio(script)
        if not audio_file:
            logger.error("Audio generation failed, aborting")
            exit(1)
        
        if not generate_rss(audio_file):
            logger.error("RSS generation failed, aborting")
            exit(1)
        
        logger.info("Podcast generation completed successfully")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)
