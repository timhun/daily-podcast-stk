import yfinance as yf
import requests
import json
import yaml
import random
import os
import logging
from datetime import datetime
from gtts import gTTS
from feedgen.feed import FeedGenerator
import time

# 設置日誌
def setup_logger():
    os.makedirs("data/logs", exist_ok=True)
    log_file = f"data/logs/podcast_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
    )
    logger = logging.getLogger(__name__)
    logger.info("Logger initialized")
    return logger

logger = setup_logger()

# 確保目錄存在
def ensure_directories():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    logger.info("Ensured audio and data directories exist")

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
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()['data']['BTC']['quote']['USD']
            logger.info(f"Fetched BTC: price={data['price']}, change={data['percent_change_24h']}%")
            return {'price': round(data['price'], 2), 'change': round(data['percent_change_24h'], 2)}
        except Exception as e:
            logger.error(f"Error fetching BTC (attempt {attempt + 1}): {str(e)}")
            time.sleep(2)
    logger.warning("Using fallback BTC data")
    return {'price': 118100, 'change': 4.03}

def fetch_gold():
    try:
        # 模擬 TradingEconomics API - 請替換為真實 API 呼叫
        data = {'price': 3354.76, 'change': 0.92}
        logger.info(f"Fetched Gold: price={data['price']}, change={data['change']}%")
        return data
    except Exception as e:
        logger.error(f"Error fetching Gold: {str(e)}")
        return None

def fetch_top_stocks():
    try:
        # 模擬 Yahoo Finance - 請替換為真實 API 呼叫以獲取熱門股票
        stocks = ['AAPL', 'NVDA', 'TSLA', 'AMZN', 'MSFT']
        logger.info(f"Fetched top stocks: {stocks}")
        return stocks
    except Exception as e:
        logger.error(f"Error fetching top stocks: {str(e)}")
        return None

def fetch_news(api_key):
    try:
        # 模擬 NewsAPI - 請替換為真實 API 呼叫
        news = {
            'ai': {'title': '最新AI模型發布', 'summary': '某公司發布了突破性的AI模型，聲稱性能大幅提升。'},
            'economic': {'title': '美國聯準會利率決議', 'summary': '聯準會宣布維持利率不變，但暗示未來可能升息。'}
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

# 生成腳本 (整合 Grok - 需使用者自行替換)
def generate_script(cmc_api_key, newsapi_key):
    logger.info("Starting script generation using Grok (Placeholder)")
    try:
        with open('podcast_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            tw_phrases = json.load(f)

        indices = fetch_indices() or {
            '^DJI': {'close': 0, 'change': 0},
            '^IXIC': {'close': 0, 'change': 0},
            '^GSPC': {'close': 0, 'change': 0},
            '^SOX': {'close': 0, 'change': 0},
            'QQQ': {'close': 0, 'change': 0},
            'SPY': {'close': 0, 'change': 0}
        }
        btc = fetch_crypto(cmc_api_key)
        gold = fetch_gold() or {'price': 0, 'change': 0}
        stocks = fetch_top_stocks() or []
        news = fetch_news(newsapi_key) or {}
        quote = fetch_quote() or {'text': 'No quote available', 'author': ''}
        date = datetime.now().strftime('%Y年%m月%d日')

        greeting = random.choice(tw_phrases['greetings'])
        positive = random.choice(tw_phrases['positive'])
        negative = random.choice(tw_phrases['negative'])
        analysis = random.choice(tw_phrases['analysis'])
        closing = random.choice(tw_phrases['closing'])

        # --- Grok 整合 Placeholder ---
        # 在此處您需要整合 Grok 的 API 呼叫，根據您的需求生成腳本
        # 腳本內容應涵蓋 (1) 到 (7) 的所有目標
        # 並符合語音風格和語速的要求
        script = f"""
《大叔說財經科技投資》 - {date}
開場白
{greeting}今天是{date}，咱們來聊聊昨天的財經大小事...
(1) 美股四大指數：道瓊 {indices['^DJI']['close']} ({indices['^DJI']['change']}%)，那斯達克 {indices['^IXIC']['close']} ({indices['^IXIC']['change']}%)，標普500 {indices['^GSPC']['close']} ({indices['^GSPC']['change']}%)，費城半導體 {indices['^SOX']['close']} ({indices['^SOX']['change']}%)...
(2) QQQ {indices['QQQ']['change']}%，SPY {indices['SPY']['change']}%，簡要分析...
(3) 比特幣 {btc['price']} ({btc['change']}%)，黃金 {gold['price']} ({gold['change']}%)，簡要分析...
(4) 熱門股：{', '.join(stocks)}，資金流向...
(5) AI新聞：{news.get('ai', {}).get('title', '')}...
(6) 美國經濟新聞：{news.get('economic', {}).get('title', '')}...
(7) 今日金句：“{quote['text']}” —— {quote['author']}。
結語
{closing}
"""
        # --- Grok 整合 Placeholder End ---

        with open('data/script.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Podcast script generated successfully")
        return script
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        return None

# 文字轉語音 (使用 gTTS)
def text_to_audio(script, output_file):
    logger.info(f"Starting text_to_audio for {output_file}")
    try:
        ensure_directories()
        tts = gTTS(text=script, lang='zh-tw', slow=False)
        temp_file = f"{output_file}.temp.mp3"
        tts.save(temp_file)
        logger.info(f"Saved temporary audio file: {temp_file}")
        # 使用 FFmpeg 加速語速至 1.3 倍
        result = os.system(f"ffmpeg -i {temp_file} -filter:a 'atempo=1.3' -y {output_file}")
        if result != 0:
            logger.error("FFmpeg command failed")
            return None
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info(f"Removed temporary file: {temp_file}")
        if not os.path.exists(output_file):
            logger.error(f"Audio file {output_file} not created")
            return None
        logger.info(f"Audio generated successfully: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return None

# 生成 RSS 饋送
def generate_rss():
    logger.info("Starting RSS generation")
    try:
        fg = FeedGenerator()
        fg.title('大叔說財經科技投資')
        fg.author({'name': '大叔', 'email': 'uncle@example.com'})
        fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate') # 請在此處替換您的 GitHub Pages URL
        fg.description('每日財經科技投資資訊，用台灣人的語言聊美股、加密貨幣、AI與美國經濟新聞')
        fg.language('zh-tw')
        fg.itunes_category({'cat': 'Business', 'sub': 'Investing'})
        fg.itunes_image('https://timhun.github.io/daily-podcast-stk/img/cover.jpg') # 請在此處替換您的 Podcast 封面圖片 URL
        fg.itunes_explicit('no')

        date = datetime.now().strftime('%Y%m%d')
        audio_file_path = f'audio/episode_{date}.mp3'
        try:
            audio_file_size = os.path.getsize(audio_file_path)
        except FileNotFoundError:
            logger.warning(f"Audio file not found: {audio_file_path}, using default length")
            audio_file_size = 45000000 # 預設檔案大小

        fe = fg.add_entry()
        fe.title(f'每日財經播報 - {date}')
        fe.description('咱們用台灣人的方式，盤點美股、加密貨幣、AI與美國經濟新聞！')
        fe.enclosure(url=f'https://timhun.github.io/daily-podcast-stk/audio/episode_{date}.mp3', type='audio/mpeg', length=str(audio_file_size)) # 請在此處替換您的 GitHub Pages URL
        fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))

        fg.rss_file('feed.xml')
        logger.info("RSS feed generated successfully")
        return True
    except Exception as e:
        logger.error(f"Error generating RSS: {str(e)}")
        return None

# 主程式
if __name__ == "__main__":
    logger.info("Starting podcast generation")
    ensure_directories()
    cmc_api_key = os.getenv('CMC_API_KEY')
    newsapi_key = os.getenv('NEWSAPI_KEY')
    if not cmc_api_key or not newsapi_key:
        logger.error("Missing API keys: CMC_API_KEY or NEWSAPI_KEY")
        exit(1)

    script = generate_script(cmc_api_key, newsapi_key)
    if script:
        date = datetime.now().strftime('%Y%m%d')
        output_file = f'audio/episode_{date}.mp3'
        if text_to_audio(script, output_file):
            generate_rss()
        else:
            logger.error("Failed to generate audio, skipping RSS generation")
    else:
        logger.error("Failed to generate script, aborting")
