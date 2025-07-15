import yfinance as yf
import json
import os
import logging
from datetime import datetime
from gtts import gTTS
from feedgen.feed import FeedGenerator
import random
import subprocess

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
    logger.info("Fetching stock indices data")
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
            logger.info(f"Fetched {idx}: close={close}, change={change}%")
        except Exception as e:
            logger.error(f"Error fetching {idx}: {e}")
            return None
    return data

# 生成播客腳本（模擬 Grok）
def generate_script():
    logger.info("Starting script generation")
    ensure_directories()
    try:
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            phrases = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load tw_phrases.json: {e}")
        return None
    
    indices = fetch_indices() or {
        '^DJI': {'close': 44371.51, 'change': -0.63},
        '^IXIC': {'close': 20585.53, 'change': -0.22},
        '^GSPC': {'close': 6259.75, 'change': -0.33},
        '^SOX': {'close': 5696.29, 'change': -0.21}
    }
    
    date = datetime.now().strftime('%Y年%m月%d日')
    script = (
        f"{random.choice(phrases['greetings'])}今天是{date}，咱們來看看昨天美股四大指數的表現！\n\n"
        f"先說道瓊指數，收在 {indices['^DJI']['close']} 點，{'漲' if indices['^DJI']['change'] >= 0 else '跌'} {abs(indices['^DJI']['change'])}%，"
        f"這表現{random.choice(phrases['analysis'])}\n"
        f"納斯達克收在 {indices['^IXIC']['close']} 點，{'漲' if indices['^IXIC']['change'] >= 0 else '跌'} {abs(indices['^IXIC']['change'])}%，"
        f"科技股這塊{random.choice(phrases['analysis'])}\n"
        f"標普500收在 {indices['^GSPC']['close']} 點，{'漲' if indices['^GSPC']['change'] >= 0 else '跌'} {abs(indices['^GSPC']['change'])}%，"
        f"市場整體感覺{random.choice(phrases['analysis'])}\n"
        f"費城半導體指數收在 {indices['^SOX']['close']} 點，{'漲' if indices['^SOX']['change'] >= 0 else '跌'} {abs(indices['^SOX']['change'])}%，"
        f"晶片股這邊{random.choice(phrases['analysis'])}\n\n"
        f"總的來說，昨天美股表現還算平穩，市場可能在找方向。大叔提醒大家，投資要穩扎穩打，別衝太快！"
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

# 文字轉語音
def text_to_audio(script):
    logger.info("Starting text-to-audio conversion")
    date = datetime.now().strftime('%Y%m%d')
    output_file = f"audio/episode_{date}.mp3"
    temp_file = "audio/temp.mp3"
    
    try:
        # 驗證 FFmpeg 安裝
        ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if ffmpeg_check.returncode != 0:
            logger.error(f"FFmpeg not installed or failed: {ffmpeg_check.stderr}")
            return None
        logger.info(f"FFmpeg version: {ffmpeg_check.stdout.splitlines()[0]}")
        
        # 使用 gTTS 生成語音
        logger.info("Generating audio with gTTS")
        tts = gTTS(text=script, lang='zh-tw', slow=False)
        tts.save(temp_file)
        if not os.path.exists(temp_file):
            logger.error(f"Temporary audio file not created: {temp_file}")
            return None
        logger.info(f"Temporary audio file created: {temp_file}")
        
        # 使用 FFmpeg 加速語音至 1.3 倍
        logger.info(f"Processing audio with FFmpeg to {output_file}")
        result = subprocess.run(
            ['ffmpeg', '-i', temp_file, '-filter:a', 'atempo=1.3', '-y', output_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg processing failed: {result.stderr}")
            return None
        
        # 清理臨時檔案
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info(f"Removed temporary file: {temp_file}")
        
        # 驗證輸出檔案
        if not os.path.exists(output_file):
            logger.error(f"Output audio file not created: {output_file}")
            return None
        logger.info(f"Audio generated successfully: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")
        return None

# 生成 RSS 饋送
def generate_rss(audio_file):
    logger.info("Starting RSS generation")
    try:
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
    except Exception as e:
        logger.error(f"RSS generation failed: {e}")
        return None

# 主執行流程
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
        logger.error(f"Unexpected error in main execution: {e}")
        exit(1)
