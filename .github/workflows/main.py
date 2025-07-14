import yfinance as yf
import json
import os
import logging
from datetime import datetime
from gtts import gTTS
from feedgen.feed import FeedGenerator
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(f"data/logs/podcast_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')]
)

logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs("audio", exist_ok=True)
os.makedirs("data/logs", exist_ok=True)

# Fetch stock indices data
def fetch_indices():
    indices = ['^DJI', '^IXIC', '^GSPC', '^SOX']
    data = {}
    for idx in indices:
        try:
            ticker = yf.Ticker(idx)
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                logger.error(f"Insufficient data for {idx}")
                return None
            close = hist['Close'][-1]
            prev_close = hist['Close'][-2]
            change = ((close - prev_close) / prev_close) * 100
            data[idx] = {'close': round(close, 2), 'change': round(change, 2)}
            logger.info(f"{idx}: {close}, {change}%")
        except Exception as e:
            logger.error(f"Error fetching {idx}: {e}")
            return None
    return data

# Generate podcast script
def generate_script():
    with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
        phrases = json.load(f)
    
    indices = fetch_indices()
    if not indices:
        logger.error("Failed to fetch indices")
        return None
    
    date = datetime.now().strftime('%Y年%m月%d日')
    script = (f"{random.choice(phrases['greetings'])}今天是{date}，咱們來看昨天美股四大指數。\n\n"
              f"道瓊指數收 {indices['^DJI']['close']} 點，{'漲' if indices['^DJI']['change'] >= 0 else '跌'} {abs(indices['^DJI']['change'])}%；\n"
              f"納斯達克收 {indices['^IXIC']['close']} 點，{'漲' if indices['^IXIC']['change'] >= 0 else '跌'} {abs(indices['^IXIC']['change'])}%；\n"
              f"標普500收 {indices['^GSPC']['close']} 點，{'漲' if indices['^GSPC']['change'] >= 0 else '跌'} {abs(indices['^GSPC']['change'])}%；\n"
              f"費半指數收 {indices['^SOX']['close']} 點，{'漲' if indices['^SOX']['change'] >= 0 else '跌'} {abs(indices['^SOX']['change'])}%。\n\n"
              f"整體來說，昨天美股{random.choice(phrases['analysis'])}。{random.choice(phrases['closing'])}")
    
    with open('data/script.txt', 'w', encoding='utf-8') as f:
        f.write(script)
    logger.info("Script generated")
    return script

# Convert text to audio
def text_to_audio(script):
    date = datetime.now().strftime('%Y%m%d')
    output = f"audio/episode_{date}.mp3"
    try:
        tts = gTTS(text=script, lang='zh-tw', slow=False)
        temp_file = "temp.mp3"
        tts.save(temp_file)
        os.system(f"ffmpeg -i {temp_file} -filter:a 'atempo=1.3' -y {output}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if not os.path.exists(output):
            logger.error("Audio file not created")
            return None
        logger.info("Audio generated")
        return output
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        return None

# Generate RSS feed
def generate_rss(audio_file):
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
    logger.info("RSS updated")
    return True

# Main execution
if __name__ == "__main__":
    script = generate_script()
    if script:
        audio_file = text_to_audio(script)
        if audio_file:
            generate_rss(audio_file)
        else:
            logger.error("Audio generation failed")
    else:
        logger.error("Script generation failed")
