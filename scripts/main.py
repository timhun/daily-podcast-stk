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
        data = {'price': 2400.50, 'change': 1.20}
        logger.info(f"Fetched Gold: price={data['price']}, change={data['change']}%")
        return data
    except Exception as e:
        logger.error(f"Error fetching Gold: {str(e)}")
        return None

def fetch_top_stocks():
    try:
        # 模擬 Yahoo Finance（需自行實現）
        stocks = ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOGL']
        logger.info(f"Fetched top stocks: {stocks}")
        return stocks
    except Exception as e:
        logger.error(f"Error fetching top stocks: {str(e)}")
        return None

def fetch_news(api_key):
    try:
        # 模擬 NewsAPI（需自行申請）
        news = {
            'ai': {'title': 'NVIDIA發佈新AI晶片', 'summary': 'NVIDIA最新H200晶片提升AI運算效能，市場熱度再創新高！'},
            'economic': {'title': '聯準會維持利率不變', 'summary': '美國經濟數據穩定，投資人關注後續通脹報告！'}
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

# 使用 xAI API 生成腳本
def generate_script(xai_api_key, cmc_api_key, newsapi_key):
    try:
        with open('podcast_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            tw_phrases = json.load(f)

        indices = fetch_indices() or {
            '^DJI': {'close': 40000.12, 'change': -0.50},
            '^IXIC': {'close': 18000.45, 'change': 0.30},
            '^GSPC': {'close': 5500.78, 'change': 0.10},
            '^SOX': {'close': 5000.23, 'change': 0.20},
            'QQQ': {'close': 450.56, 'change': 0.25},
            'SPY': {'close': 500.89, 'change': 0.15}
        }
        btc = fetch_crypto(cmc_api_key) or {'price': 60000.00, 'change': 2.50}
        gold = fetch_gold() or {'price': 2400.50, 'change': 1.20}
        stocks = fetch_top_stocks() or ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOGL']
        news = fetch_news(newsapi_key) or {
            'ai': {'title': 'NVIDIA發佈新AI晶片', 'summary': 'NVIDIA最新H200晶片提升AI運算效能！'},
            'economic': {'title': '聯準會維持利率不變', 'summary': '美國經濟數據穩定！'}
        }
        quote = fetch_quote() or {'text': '投資像種樹，今天種下，十年後才乘涼！', 'author': '大叔'}
        date = datetime.now().strftime('%Y年%m月%d日')

        # 構建 xAI API 提示
        prompt = f"""
        請以親切自然的台灣中年大叔風格，生成一篇約2000-2200字的《大叔說財經科技投資》Podcast腳本，日期為{date}。使用台灣慣用語（如{tw_phrases['greetings'][0]}、{tw_phrases['positive'][0]}、{tw_phrases['negative'][0]}、{tw_phrases['analysis'][0]}、{tw_phrases['closing'][0]}），語氣輕鬆接地氣，專業與親切平衡。腳本結構如下：
        1. 開場白：熱情問候，介紹日期與節目內容。
        2. 美股四大指數：道瓊({indices['^DJI']['close']}點，{indices['^DJI']['change']}%)、納斯達克({indices['^IXIC']['close']}點，{indices['^IXIC']['change']}%)、標普500({indices['^GSPC']['close']}點，{indices['^GSPC']['change']}%)、費城半導體({indices['^SOX']['close']}點，{indices['^SOX']['change']}%)，附簡易分析。
        3. QQQ與SPY ETF：QQQ({indices['QQQ']['close']}，{indices['QQQ']['change']}%)、SPY({indices['SPY']['close']}，{indices['SPY']['change']}%)，附簡易分析。
        4. 比特幣與黃金期貨：比特幣({btc['price']}美元，{btc['change']}%)、黃金({gold['price']}美元/盎司，{gold['change']}%)，附簡易分析。
        5. Top 5熱門股：{', '.join(stocks)}，簡述資金流向與分析。
        6. AI新聞：{news['ai']['title']}，{news['ai']['summary']}，附簡易影響分析。
        7. 美國經濟新聞：{news['economic']['title']}，{news['economic']['summary']}，附簡易影響分析。
        8. 每日投資金句："{quote['text']}" —— {quote['author']}，附大叔式提醒。
        9. 結語：總結。
        請確保腳本約15分鐘（語速1.3倍，130-150字/分鐘）。
        """

        # 調用 xAI API
        xai_url = "https://api.x.ai/v1/grok"
        headers = {'Authorization': f'Bearer {xai_api_key}'}
        payload = {'prompt': prompt}
        response = requests.post(xai_url, headers=headers, json=payload)
        response.raise_for_status()
        script = response.json()['response']

        # 儲存逐字稿
        os.makedirs('transcripts', exist_ok=True)
        transcript_file = f"transcripts/episode_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info(f"Transcript saved: {transcript_file}")

        # 儲存腳本
        with open('data/script.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Podcast script generated successfully")
        return script
    except Exception as e:
        logger.error(f"Error generating script with xAI API: {str(e)}")
        return None

# 文字轉語音
def text_to_audio(script, output_file):
    try:
        tts = gTTS(text=script, lang='zh-tw', slow=False)
        tts.save(output_file)
        # 使用 FFmpeg 調整語速至 1.3 倍
        os.system(f"ffmpeg -i {output_file} -filter:a 'atempo=1.3' -y {output_file}")
        logger.info(f"Audio generated: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return None

# 生成 RSS 饋送
def generate_rss():
    try:
        fg = FeedGenerator()
        fg.title('大叔說財經科技投資')
        fg.author({'name': '大叔', 'email': 'uncle@example.com'})
        fg.link(href='https://timhun.github.io/daily-podcast/', rel='alternate')
        fg.description('每日財經科技投資資訊，聊美股、加密貨幣、AI與經濟新聞')
        fg.language('zh-tw')
        fg.itunes_category({'cat': 'Business', 'sub': 'Investing'})
        fg.itunes_image('https://timhun.github.io/daily-podcast/img/cover.jpg')
        fg.itunes_explicit('no')

        date = datetime.now().strftime('%Y%m%d')
        fe = fg.add_entry()
        fe.title(f'每日財經播報 - {date}')
        fe.description('盤點美股、加密貨幣、AI與經濟新聞！')
        fe.enclosure(url=f'https://timhun.github.io/daily-podcast/audio/episode_{date}.mp3', type='audio/mpeg', length='45000000')
        fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))

        fg.rss_file('feed.xml')
        logger.info("RSS feed generated successfully")
        return True
    except Exception as e:
        logger.error(f"Error generating RSS: {str(e)}")
        return None

# 主程式
if __name__ == "__main__":
    xai_api_key = os.getenv('XAI_API_KEY')
    cmc_api_key = os.getenv('CMC_API_KEY')
    newsapi_key = os.getenv('NEWSAPI_KEY')
    
    script = generate_script(xai_api_key, cmc_api_key, newsapi_key)
    if script:
        date = datetime.now().strftime('%Y%m%d')
        output_file = f'audio/episode_{date}.mp3'
        if text_to_audio(script, output_file):
            generate_rss()
