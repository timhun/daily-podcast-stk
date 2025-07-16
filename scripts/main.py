import yfinance as yf
import json
import os
import logging
from datetime import datetime, timedelta
from gtts import gTTS
import random
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator
import time

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
logger.info("日誌初始化完成")

# 確保目錄存在
def ensure_directories():
    os.makedirs("audio", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/scripts", exist_ok=True)
    logger.info("確保目錄存在")

# 獲取財經數據（含重試邏輯）
def fetch_financial_data():
    logger.info("開始獲取財經數據")
    tickers = {
        'indices': ['^DJI', '^IXIC', '^GSPC', '^SOX'],
        'etfs': ['QQQ']
    }
    data = {'indices': {}, 'etfs': {}}
    
    for category, symbols in tickers.items():
        for sym in symbols:
            attempts = 5  # 增加重試次數
            for attempt in range(1, attempts + 1):
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='5d')  # 獲取 5 天數據以避免缺失
                    if len(hist) < 2:
                        logger.error(f"嘗試 {attempt}：{sym} 數據不足")
                        if attempt == attempts:
                            logger.warning(f"跳過 {sym}，使用備用數據")
                            return None
                        time.sleep(3)
                        continue
                    close = hist['Close'][-1]
                    prev_close = hist['Close'][-2]
                    change = ((close - prev_close) / prev_close) * 100
                    data[category][sym] = {'close': round(close, 2), 'change': round(change, 2)}
                    logger.info(f"獲取 {sym}：收盤={close}, 漲跌={change}%")
                    break
                except Exception as e:
                    logger.error(f"嘗試 {attempt}：獲取 {sym} 失敗：{e}")
                    if attempt == attempts:
                        logger.warning(f"跳過 {sym}，使用備用數據")
                        return None
                    time.sleep(3)
    
    return data

# 使用 Grok 3 生成腳本
def generate_script():
    logger.info("開始使用 Grok 3 生成腳本")
    ensure_directories()
    try:
        with open('scripts/tw_phrases.json', 'r', encoding='utf-8') as f:
            phrases = json.load(f)
    except Exception as e:
        logger.error(f"無法載入 tw_phrases.json：{e}")
        return None, None
    
    data = fetch_financial_data() or {
        'indices': {
            '^DJI': {'close': 44371.51, 'change': -0.63},
            '^IXIC': {'close': 20585.53, 'change': -0.22},
            '^GSPC': {'close': 6259.75, 'change': -0.33},
            '^SOX': {'close': 5696.29, 'change': -0.21}
        },
        'etfs': {
            'QQQ': {'close': 500.12, 'change': -0.15}
        }
    }
    
    # 使用前一天日期（內容反映前日收盤），檔案名使用當天日期
    date = (datetime.now() - timedelta(days=1)).strftime('%Y年%m月%d日')
    file_date = datetime.now().strftime('%Y%m%d')
    
    prompt = f"""
    你是大叔，一位親切、風趣的台灣中年男性，擅長用台灣慣用語以輕鬆的方式解說財經資訊。請根據以下數據，撰寫一篇約 400-500 字的播客逐字稿，語氣親切自然，帶點幽默，融入以下台灣慣用語：
    - 開場：{random.choice(phrases['greetings'])}
    - 漲跌分析：正向用「{phrases['analysis_positive'][0]}」「{phrases['analysis_positive'][1]}」「{phrases['analysis_positive'][2]}」，負向用「{phrases['analysis_negative'][0]}」「{phrases['analysis_negative'][1]}」「{phrases['analysis_negative'][2]}」
    - 結尾：{phrases['closing'][0]} 或 {phrases['closing'][1]} 或 {phrases['closing'][2]}

    內容結構：
    1. 開場問候，提到日期（{date}）。
    2. 美股四大指數（道瓊、納斯達克、標普500、費城半導體）收盤數據與漲跌幅，簡短評論。
    3. QQQ ETF 收盤與漲跌幅，簡易分析（例如科技股穩定或波動）。
    4. 結尾以幽默語氣總結。

    數據：
    - 道瓊 (^DJI): {data['indices']['^DJI']['close']} 點，{'漲' if data['indices']['^DJI']['change'] >= 0 else '跌'} {abs(data['indices']['^DJI']['change'])}%
    - 納斯達克 (^IXIC): {data['indices']['^IXIC']['close']} 點，{'漲' if data['indices']['^IXIC']['change'] >= 0 else '跌'} {abs(data['indices']['^IXIC']['change'])}%
    - 標普500 (^GSPC): {data['indices']['^GSPC']['close']} 點，{'漲' if data['indices']['^GSPC']['change'] >= 0 else '跌'} {abs(data['indices']['^GSPC']['change'])}%
    - 費城半導體 (^SOX): {data['indices']['^SOX']['close']} 點，{'漲' if data['indices']['^SOX']['change'] >= 0 else '跌'} {abs(data['indices']['^SOX']['change'])}%
    - QQQ: {data['etfs']['QQQ']['close']} 點，{'漲' if data['etfs']['QQQ']['change'] >= 0 else '跌'} {abs(data['etfs']['QQQ']['change'])}%

    語氣需親切、幽默，控制在 15 分鐘語音長度（約 400-500 字）。確保逐字稿結構清晰，分段明確。
    """
    
    try:
        client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
        response = client.chat.completions.create(
            model="grok",  # Grok 3 模型
            messages=[
                {"role": "system", "content": "你是一位親切、風趣的台灣中年大叔，擅長用台灣慣用語解說財經資訊。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        script = response.choices[0].message.content
        with open(f'data/scripts/script_{file_date}.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Grok 3 腳本生成成功")
        return script, file_date
    except Exception as e:
        logger.error(f"Grok 3 API 失敗：{e}")
        # 備用腳本
        analysis = lambda x: random.choice(phrases['analysis_positive'] if x >= 0 else phrases['analysis_negative'])
        script = (
            f"{random.choice(phrases['greetings'])}今天是{date}，大叔帶你看財經市場的最新動態！\n\n"
            f"### 1. 美股四大指數\n"
            f"先來看美股四大指數的表現：\n"
            f"- 道瓊指數收在 {data['indices']['^DJI']['close']} 點，{'漲' if data['indices']['^DJI']['change'] >= 0 else '跌'} {abs(data['indices']['^DJI']['change'])}%，{analysis(data['indices']['^DJI']['change'])}\n"
            f"- 納斯達克收在 {data['indices']['^IXIC']['close']} 點，{'漲' if data['indices']['^IXIC']['change'] >= 0 else '跌'} {abs(data['indices']['^IXIC']['change'])}%，{analysis(data['indices']['^IXIC']['change'])}\n"
            f"- 標普500收在 {data['indices']['^GSPC']['close']} 點，{'漲' if data['indices']['^GSPC']['change'] >= 0 else '跌'} {abs(data['indices']['^GSPC']['change'])}%，{analysis(data['indices']['^GSPC']['change'])}\n"
            f"- 費城半導體收在 {data['indices']['^SOX']['close']} 點，{'漲' if data['indices']['^SOX']['change'] >= 0 else '跌'} {abs(data['indices']['^SOX']['change'])}%，{analysis(data['indices']['^SOX']['change'])}\n\n"
            f"### 2. QQQ ETF 動態\n"
            f"看看 QQQ（科技股 ETF）：收在 {data['etfs']['QQQ']['close']} 點，{'漲' if data['etfs']['QQQ']['change'] >= 0 else '跌'} {abs(data['etfs']['QQQ']['change'])}%，科技股{'穩定' if abs(data['etfs']['QQQ']['change']) < 1 else '波動較大'}。\n\n"
            f"### 3. 總結\n"
            f"{random.choice(phrases['closing'])}"
        )
        with open(f'data/scripts/script_{file_date}.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("生成備用腳本")
        return script, file_date

# 文字轉語音
def text_to_audio(script, file_date):
    logger.info("開始文字轉語音")
    output_file = f"audio/episode_{file_date}.mp3"
    temp_file = "audio/temp.mp3"
    fallback_file = "audio/fallback.mp3"
    
    try:
        # 檢查 FFmpeg
        ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if ffmpeg_check.returncode != 0:
            logger.error(f"FFmpeg 未安裝：{ffmpeg_check.stderr}")
            return fallback_file
        logger.info(f"FFmpeg 版本：{ffmpeg_check.stdout.splitlines()[0]}")
        
        # 生成語音
        logger.info("使用 gTTS 生成語音")
        tts = gTTS(text=script, lang='zh-TW', slow=False)
        tts.save(temp_file)
        if not os.path.exists(temp_file):
            logger.error(f"臨時音頻檔案未生成：{temp_file}")
            return fallback_file
        logger.info(f"臨時音頻檔案生成：{temp_file}")
        
        # 使用 FFmpeg 加速語音
        logger.info(f"處理音頻至 {output_file}")
        result = subprocess.run(
            ['ffmpeg', '-i', temp_file, '-filter:a', 'atempo=1.3', '-c:a', 'mp3', '-y', output_file],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg 處理失敗：{result.stderr}")
            return fallback_file
        
        # 清理臨時檔案
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info(f"刪除臨時檔案：{temp_file}")
        
        # 驗證輸出檔案
        if not os.path.exists(output_file):
            logger.error(f"輸出音頻檔案未生成：{output_file}")
            return fallback_file
        logger.info(f"音頻生成成功：{output_file}")
        
        # 檢查檔案是否為有效 MP3
        result = subprocess.run(['ffprobe', '-v', 'error', output_file], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"音頻檔案無效：{result.stderr}")
            return fallback_file
        logger.info(f"音頻檔案驗證通過：{output_file}")
        
        return output_file
    except Exception as e:
        logger.error(f"音頻生成失敗：{str(e)}")
        return fallback_file

# 生成 RSS

def generate_rss(audio_file):
    logger.info("開始生成 RSS")
    try:
        fg = FeedGenerator()
        fg.load_extension('itunes')  # 啟用 iTunes 擴展
        fg.title('幫幫忙說財經科技投資')
        fg.itunes_author('幫幫忙')  # 明確設置 iTunes 作者
        fg.author({'name': '幫幫忙', 'email': 'podcast@timhun.github.io'})  # 標準 RSS 作者
        fg.link(href='https://timhun.github.io/daily-podcast-stk/', rel='alternate')
        fg.description('每日美股指數與 QQQ ETF 動態，用台灣味聊投資')
        fg.language('zh-tw')
        fg.itunes_category({'cat': 'Business', 'sub': 'Investing'})  # 添加 iTunes 分類
        fg.itunes_explicit('no')  # 明確內容分級
        
        date = datetime.now().strftime('%Y%m%d')
        fe = fg.add_entry()
        fe.title(f'美股播報 - {date}')
        fe.description('幫幫忙帶你看美股四大指數與 QQQ ETF 動態！')
        fe.enclosure(url=f'https://timhun.github.io/daily-podcast-stk/audio/episode_{date}.mp3', type='audio/mpeg', length='45000000')
        fe.published(datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
        fe.guid(f"episode_{date}", permalink=False)  # 唯一 GUID
        
        fg.rss_file('feed.xml')
        logger.info("RSS 檔案更新成功")
        return True
    except Exception as e:
        logger.error(f"RSS 生成失敗：{e}")
        return None

# 主程式
if __name__ == "__main__":
    logger.info("開始生成播客")
    try:
        if not os.getenv("XAI_API_KEY"):
            logger.error("XAI_API_KEY 未設置")
            exit(1)
        
        script, file_date = generate_script()
        if not script:
            logger.error("腳本生成失敗，中止")
            exit(1)
        
        audio_file = text_to_audio(script, file_date)
        if not audio_file or not os.path.exists(audio_file):
            logger.error(f"音頻檔案 {audio_file} 不存在，中止")
            exit(1)
        
        if not generate_rss(audio_file, file_date):
            logger.error("RSS 生成失敗，中止")
            exit(1)
        
        logger.info("播客生成成功完成")
    except Exception as e:
        logger.error(f"意外錯誤：{e}")
        exit(1)
