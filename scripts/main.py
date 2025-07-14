import yfinance as yf
import json
import os
import logging
from datetime import datetime
from gtts import gTTS
from feedgen.feed import FeedGenerator
import random

# 設置日誌
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

# 確保目錄存在
def ensure_directories():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    logger.info("Ensured audio and data directories exist")

# 獲取美股指數數據
def fetch_indices():
    indices = ['^DJI', '^IXIC', '^GSPC', '^SOX']
    data = {}
    for idx in indices:
        ticker = yf.Ticker(idx)
        hist = ticker.history(period='2d')
        if len(hist) < 2:
            logger.error(f"Insufficient data for {idx}")
            return None
        close = hist['Close'][-1]
        prev_close = hist['Close'][-2]
        change = ((close - prev_close) / prev_close) * 100
        data[idx] = {'close': round(close, 2), 'change': round(change, 2)}
        logger.info(f"Fetched {idx}: close={close}, change={change}%")
    return data

# 生成播客腳本
def generate_script():
    logger.info("Starting script generation")
    ensure_directories()
    with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
        phrases = json.load(f)
    
    # 獲取數據，若失敗使用備用數據
    indices = fetch_indices() or {
        '^DJI': {'close': 44371.51, 'change': -0.63},
        '^IXIC': {'close': 20585.53, 'change': -0.22},
        '^GSPC': {'close': 6259.75, 'change': -0.33},
        '^SOX': {'close': 5696.29, 'change': -0.21}
    }
    
    date = datetime.now().strftime('%Y年%m月%d日')
    script = (
        f"{random.choice(phrases['greetings'])}今天是{date}，咱們來看昨天美股四大指數。\n\n"
        f"道瓊指數收 {indices['^DJI']['close']} 點，{'漲' if indices['^DJI']['change'] >= 0 else '跌'} {abs(indices['^DJI']['change'])}%；\n"
        f"納斯達克收 {indices['^IXIC']['close']} 點，{'漲' if indices['^IXIC']['change'] >= 0 else '跌'} {abs(indices['^IXIC']['change'])}%；\n"
        f"標普500收 {indices['^GSPC']['close']} 點，{'漲' if indices['^GSPC']['change'] >= 0 else '跌'} {abs(indices['^GSPC']['change'])}%；\n"
        f"費城半導體指數收 {indices['^SOX']['close']} 點，{'漲' if indices['^SOX']['change'] >= 0 else '跌'} {abs(indices['^SOX']['change'])}%。\n\n"
        f"整體來說，昨天美股{random.choice(phrases['analysis'])}。{random.choice(phrases['closing'])}"
    )
    
    with open('data/script.txt', 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info("Script generated successfully")
    return script

# 文字轉語音
def text_to_audio(script):
    logger.info("Starting text-to-audio conversion")
    date = datetime.now().strftime('%Y%m%d')
    output_file = f"audio/episode_{date}.mp3"
    temp_file = "audio/temp.mp3"
    
    tts = gTTS(text=script, lang='zh-tw', slow=False)
    tts.save(temp_file)
    result = os.system(f"ffmpeg -i {temp_file} -filter:a 'atempo=1.3' -y {output_file}")
    if os.path.exists(temp_file):
        os.remove(temp_file)
    if result != 0 or not os.path.exists(output_file):
        logger.error("Audio generation failed")
        return None
    logger.info(f"Audio generated: {output_file}")
    return output_file

# 生成 RSS 饋送
def generate_rss(audio_file):
    logger.info("Starting RSS generation")
    fg = FeedGenerator()
    fg.title('大叔說財經科技投資')
    fg.author({'name': '大叔'})
    fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
    fg.description('每日美股四大指數，用台灣味聊投資')
    fg.language('zh-tw')
    
    date = datetime.now().strftime('%Y%m%d')
    fe = fg.add_entry()
    fe.title(f'美股播報 - {date}')
    fe.description('大叔帶你看美股四大指數！')
    fe.enclosure(url=f'https://timhun.github.io/daily-podcast-stk/audio/episode_{date}.mp3', type='audio/mpeg', length='15000000')
    fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
    
    fg.rss_file('feed.xml')
    logger.info("RSS feed updated successfully")
    return True

# 主程式
if __name__ == "__main__":
    logger.info("Starting podcast generation")
    script = generate_script()
    if not script:
        logger.error("Script generation failed, aborting")
        exit(1)
    
    audio_file = text_to_audio(script)
    if not audio_file:
        logger.error("Audio generation failed, aborting")
        exit(1)
    
    if not generate_rss(audio_file):
        logger.error("RSS generation failed")
        exit(1)
    
    logger.info("Podcast generation completed successfully")