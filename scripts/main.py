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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(f"data/logs/podcast_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')]
)
logger = logging.getLogger(__name__)

# 獲取美股指數數據
def fetch_indices():
    indices = ['^DJI', '^IXIC', '^GSPC', '^SOX']
    data = {}
    for idx in indices:
        ticker = yf.Ticker(idx)
        hist = ticker.history(period='2d')
        close = hist['Close'][-1]
        prev_close = hist['Close'][-2]
        change = ((close - prev_close) / prev_close) * 100
        data[idx] = {'close': round(close, 2), 'change': round(change, 2)}
    return data

# 生成腳本
def generate_script():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
        phrases = json.load(f)
    
    indices = fetch_indices()
    date = datetime.now().strftime('%Y年%m月%d日')
    script = (
        f"{random.choice(phrases['greetings'])}今天是{date}，咱們來看昨天美股四大指數。\n\n"
        f"道瓊指數收 {indices['^DJI']['close']} 點，{'漲' if indices['^DJI']['change'] >= 0 else '跌'} {abs(indices['^DJI']['change'])}%，"
        f"這表現{random.choice(phrases['analysis'])}；\n"
        f"納斯達克收 {indices['^IXIC']['close']} 點，{'漲' if indices['^IXIC']['change'] >= 0 else '跌'} {abs(indices['^IXIC']['change'])}%；\n"
        f"標普500收 {indices['^GSPC']['close']} 點，{'漲' if indices['^GSPC']['change'] >= 0 else '跌'} {abs(indices['^GSPC']['change'])}%；\n"
        f"費城半導體收 {indices['^SOX']['close']} 點，{'漲' if indices['^SOX']['change'] >= 0 else '跌'} {abs(indices['^SOX']['change'])}%。\n\n"
        f"{random.choice(phrases['closing'])}"
    )
    with open('data/script.txt', 'w', encoding='utf-8') as f:
        f.write(script)
    return script

# 文字轉語音
def text_to_audio(script):
    date = datetime.now().strftime('%Y%m%d')
    output_file = f"audio/episode_{date}.mp3"
    tts = gTTS(text=script, lang='zh-tw', slow=False)
    tts.save("audio/temp.mp3")
    subprocess.run(['ffmpeg', '-i', 'audio/temp.mp3', '-filter:a', 'atempo=1.3', '-y', output_file])
    os.remove("audio/temp.mp3")
    return output_file

# 生成 RSS 饋送
def generate_rss(audio_file):
    fg = FeedGenerator()
    fg.title('大叔說財經科技投資')
    fg.author({'name': '大叔'})
    fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
    fg.description('每日美股四大指數，用台灣味聊投資')
    fg.language('zh-tw')