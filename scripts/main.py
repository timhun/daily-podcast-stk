import yfinance as yf
import json
import os
import logging
from datetime import datetime
import random
import requests
from openai import OpenAI
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator
import time
import subprocess
import tempfile

# Load environment variables
load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

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

# Ensure directories exist
def ensure_directories():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    logger.info("Directories ensured")

# Fetch financial data with retry logic
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
            attempts = 3
            for attempt in range(1, attempts + 1):
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='2d')
                    if len(hist) < 2:
                        logger.error(f"Attempt {attempt}: {sym} insufficient data")
                        if attempt == attempts:
                            return None
                        time.sleep(2)
                        continue
                    close = hist['Close'][-1]
                    prev_close = hist['Close'][-2]
                    change = ((close - prev_close) / prev_close) * 100
                    data[category][sym] = {'close': round(close, 2), 'change': round(change, 2)}
                    logger.info(f"Fetched {sym}: Close={close}, Change={change}%")
                    break
                except Exception as e:
                    logger.error(f"Attempt {attempt}: Failed to fetch {sym}: {e}")
                    if attempt == attempts:
                        logger.error(f"{sym} failed after {attempts} attempts")
                        return None
                    time.sleep(2)
    
    trending_stocks = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
    data['trending_stocks'] = {}
    for stock in trending_stocks:
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                ticker = yf.Ticker(stock)
                hist = ticker.history(period='2d')
                if len(hist) < 2:
                    logger.error(f"Attempt {attempt}: {stock} insufficient data")
                    if attempt == attempts:
                        return None
                    time.sleep(2)
                    continue
                close = hist['Close'][-1]
                prev_close = hist['Close'][-2]
                change = ((close - prev_close) / prev_close) * 100
                data['trending_stocks'][stock] = {'close': round(close, 2), 'change': round(change, 2)}
                logger.info(f"Fetched trending stock {stock}: Close={close}, Change={change}%")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt}: Failed to fetch {stock}: {e}")
                if attempt == attempts:
                    logger.error(f"{stock} failed after {attempts} attempts")
                    return None
                time.sleep(2)
    
    indices_avg_change = sum(data['indices'][idx]['change'] for idx in data['indices']) / len(data['indices'])
    data['fund_flow'] = "資金流入" if indices_avg_change > 0 else "資金流出"
    logger.info(f"Fund flow: {data['fund_flow']}")
    
    return data

# Fetch AI news
def fetch_ai_news():
    logger.info("Fetching AI news")
    try:
        url = f"https://newsapi.org/v2/top-headlines?category=technology&q=AI&language=en&apiKey={NEWSAPI_KEY}"
        response = requests.get(url, timeout=10)
        articles = response.json().get('articles', [])
        if articles:
            news = articles[0]['title'] + " - " + articles[0]['description'][:100] + "..."
            logger.info(f"AI news fetched: {news}")
            return news
        logger.warning("No AI news found")
        return "今天沒有特別的 AI 新聞，但 AI 持續改變世界！"
    except Exception as e:
        logger.error(f"Failed to fetch AI news: {e}")
        return "今天沒有特別的 AI 新聞，但 AI 持續改變世界！"

# Fetch economic news
def fetch_economic_news():
    logger.info("Fetching economic news")
    try:
        url = f"https://newsapi.org/v2/top-headlines?category=business&country=us&apiKey={NEWSAPI_KEY}"
        response = requests.get(url, timeout=10)
        articles = response.json().get('articles', [])
        if articles:
            news = articles[0]['title'] + " - " + articles[0]['description'][:100] + "..."
            logger.info(f"Economic news fetched: {news}")
            return news
        logger.warning("No economic news found")
        return "今天沒有特別的經濟新聞，市場穩穩走！"
    except Exception as e:
        logger.error(f"Failed to fetch economic news: {e}")
        return "今天沒有特別的經濟新聞，市場穩穩走！"

# Generate podcast script using Grok 3
def generate_script():
    logger.info("Generating podcast script with Grok 3")
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
    ai_news = fetch_ai_news()
    economic_news = fetch_economic_news()
    
    prompt = f"""
    你是大叔，一位親切、風趣的台灣中年男性，擅長用台灣慣用語以輕鬆的方式解說財經科技資訊。請根據以下數據和要求，撰寫一篇約 400-500 字的播客逐字稿，語氣要像台灣大叔，親切自然，帶點幽默，融入以下台灣慣用語：
    - 開場：{random.choice(phrases['greetings'])}
    - 漲跌分析：正向用「{phrases['analysis_positive'][0]}」「{phrases['analysis_positive'][1]}」「{phrases['analysis_positive'][2]}」，負向用「{phrases['analysis_negative'][0]}」「{phrases['analysis_negative'][1]}」「{phrases['analysis_negative'][2]}」
    - 新聞開場：{phrases['news_intro'][0]} 或 {phrases['news_intro'][1]} 或 {phrases['news_intro'][2]}
    - 結尾：{phrases['closing'][0]} 或 {phrases['closing'][1]} 或 {phrases['closing'][2]}
    - 投資金句：{phrases['investment_quotes'][0]} 或 {phrases['investment_quotes'][1]} 或 {phrases['investment_quotes'][2]}

    內容結構：
    1. 開場問候，提到日期（{date}）。
    2. 美股四大指數（道瓊、納斯達克、標普500、費城半導體）收盤數據與漲跌幅，簡短評論。
    3. QQQ、SPY、IBIT ETF 收盤與漲跌幅，簡易分析（例如科技股穩定、市場震盪、加密貨幣熱度）。
    4. 比特幣、黃金期貨報價與漲跌幅，十年期美國國債殖利率，簡易分析（例如避險需求、市場預期）。
    5. Top 5 熱門美股（AAPL, MSFT, NVDA, TSLA, GOOGL）收盤與漲跌幅，總體資金流向（{data['fund_flow']}）。
    6. 一則 AI 新聞：{ai_news}
    7. 一則美國經濟新聞：{economic_news}
    8. 結尾以每日投資金句結束。

    數據：
    - 道瓊 (^DJI): {data['indices']['^DJI']['close']} 點，{'漲' if data['indices']['^DJI']['change'] >= 0 else '跌'} {abs(data['indices']['^DJI']['change'])}%
    - 納斯達克 (^IXIC): {data['indices']['^IXIC']['close']} 點，{'漲' if data['indices']['^IXIC']['change'] >= 0 else '跌'} {abs(data['indices']['^IXIC']['change'])}%
    - 標普500 (^GSPC): {data['indices']['^GSPC']['close']} 點，{'漲' if data['indices']['^GSPC']['change'] >= 0 else '跌'} {abs(data['indices']['^GSPC']['change'])}%
    - 費城半導體 (^SOX): {data['indices']['^SOX']['close']} 點，{'漲' if data['indices']['^SOX']['change'] >= 0 else '跌'} {abs(data['indices']['^SOX']['change'])}%
    - QQQ: {data['etfs']['QQQ']['close']} 點，{'漲' if data['etfs']['QQQ']['change'] >= 0 else '跌'} {abs(data['etfs']['QQQ']['change'])}%
    - SPY: {data['etfs']['SPY']['close']} 點，{'漲' if data['etfs']['SPY']['change'] >= 0 else '跌'} {abs(data['etfs']['SPY']['change'])}%
    - IBIT: {data['etfs']['IBIT']['close']} 點，{'漲' if data['etfs']['IBIT']['change'] >= 0 else '跌'} {abs(data['etfs']['IBIT']['change'])}%
    - 比特幣 (BTC-USD): {data['crypto_commodities']['BTC-USD']['close']} 美元，{'漲' if data['crypto_commodities']['BTC-USD']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['BTC-USD']['change'])}%
    - 黃金期貨 (GC=F): {data['crypto_commodities']['GC=F']['close']} 美元，{'漲' if data['crypto_commodities']['GC=F']['change'] >= 0 else '跌'} {abs(data['crypto_commodities']['GC=F']['change'])}%
    - 十年期國債殖利率 (^TNX): {data['treasury']['^TNX']['close']}%，{'上升' if data['treasury']['^TNX']['change'] >= 0 else '下降'} {abs(data['treasury']['^TNX']['change'])}%
    - 熱門股：
      - 蘋果 (AAPL): {data['trending_stocks']['AAPL']['close']} 美元，{'漲' if data['trending_stocks']['AAPL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['AAPL']['change'])}%
      - 微軟 (MSFT): {data['trending_stocks']['MSFT']['close']} 美元，{'漲' if data['trending_stocks']['MSFT']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['MSFT']['change'])}%
      - 輝達 (NVDA): {data['trending_stocks']['NVDA']['close']} 美元，{'漲' if data['trending_stocks']['NVDA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['NVDA']['change'])}%
      - 特斯拉 (TSLA): {data['trending_stocks']['TSLA']['close']} 美元，{'漲' if data['trending_stocks']['TSLA']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['TSLA']['change'])}%
      - 谷歌 (GOOGL): {data['trending_stocks']['GOOGL']['close']} 美元，{'漲' if data['trending_stocks']['GOOGL']['change'] >= 0 else '跌'} {abs(data['trending_stocks']['GOOGL']['change'])}%

    語氣需親切、幽默，控制在 15 分鐘語音長度（約 400-500 字）。確保逐字稿結構清晰，分段明確。
    """
    
    models = ["grok-3", "grok-4-0709"]  # Try multiple models for robustness
    for model in models:
        try:
            client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位親切、風趣的台灣中年大叔，擅長用台灣慣用語解說財經科技資訊。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            script = response.choices[0].message.content
            with open('data/script.txt', 'w', encoding='utf-8') as f:
                f.write(script)
            logger.info(f"Grok 3 script generated successfully with model {model}")
            return script
        except Exception as e:
            logger.error(f"Grok API failed with model {model}: {e}")
    
    logger.error("All Grok models failed, using fallback script")
    # Fallback script
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
        f"{random.choice(phrases['news_intro'])}\n{ai_news}\n\n"
        f"### 6. 經濟新聞\n"
        f"{random.choice(phrases['news_intro'])}\n{economic_news}\n\n"
        f"### 7. 今日投資金句\n"
        f"{random.choice(phrases['investment_quotes'])}\n\n"
        f"{random.choice(phrases['closing'])}"
    )
    with open('data/script.txt', 'w', encoding='utf-8') as f:
        f.write(script Ascent
    logger.info("Generated fallback script")
    return script

# Text to audio using edge-tts
def text_to_audio(script):
    logger.info("Starting text-to-speech with edge-tts")
    date = datetime.now().strftime('%Y%m%d')
    output_file = f"audio/episode_{date}.mp3"
    
    if not script or not isinstance(script, str) or len(script.strip()) == 0:
        logger.error("Invalid or empty script provided to edge-tts")
        return None
    
    try:
        # Verify edge-tts is installed
        edge_tts_check = subprocess.run(['edge-tts'], capture_output=True, text=True)
        if edge_tts_check.returncode != 0:
            logger.error(f"edge-tts not installed: {edge_tts_check.stderr}")
            return None
        logger.info(f"edge-tts version: {edge_tts_check.stdout.strip()}")
        
        # Write script to a temporary file to avoid command-line length limits
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as temp_file:
            temp_file.write(script)
            temp_file_path = temp_file.name
        
        logger.info(f"Generating audio with edge-tts using temporary file: {temp_file_path}")
        voices = ['zh-TW-YunJheNeural', 'zh-TW-HsiaoYuNeural']  # Fallback voices
        for voice in voices:
            try:
                result = subprocess.run(
                    ['edge-tts', '--voice', voice, '--file', temp_file_path, '--write-media', output_file, '--rate=+30%'],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and os.path.exists(output_file):
                    logger.info(f"Audio generated successfully with voice {voice}: {output_file}")
                    os.remove(temp_file_path)  # Clean up temporary file
                    return output_file
                logger.error(f"edge-tts failed with voice {voice}: {result.stderr}")
            except Exception as e:
                logger.error(f"edge-tts failed with voice {voice}: {str(e)}")
        
        logger.error("All voices failed")
        os.remove(temp_file_path)  # Clean up even on failure
        return None
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")
        if 'temp_file_path' in locals():
            os.remove(temp_file_path)  # Clean up in case of error
        return None

# Generate RSS feed
def generate_rss(audio_file):
    logger.info("Generating RSS feed")
    try:
        fg = FeedGenerator()
        fg.title('幫幫忙說財經科技投資')
        fg.author({'name': '大叔'})
        fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
        fg.description('每日美股、ETF、比特幣、AI與經濟新聞，用台灣味聊投資')
        fg.language('zh-tw')
        
        date = datetime.now().strftime('%Y%m%d')
        fe = fg.add_entry()
        fe.title(f'美股與科技播報 - {date}')
        fe.description('大叔帶你看美股、ETF、比特幣與最新財經動態！')
        fe.enclosure(url=f'https://timhun.github.io/daily-podcast-stk/audio/episode_{date}.mp3', type='audio/mpeg', length='45000000')
        fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
        
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
        if not XAI_API_KEY:
            logger.error("XAI_API_KEY not set")
            exit(1)
        if not NEWSAPI_KEY:
            logger.error("NEWSAPI_KEY not set")
            exit(1)
        
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
