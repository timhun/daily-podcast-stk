import os
import datetime
import pytz
import xml.etree.ElementTree as ET
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator
from loguru import logger
import json
from cloud_manager import upload_rss
from slack_sdk import WebClient

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 設置日誌
logger.add(config['logging']['file'], rotation=config['logging']['rotation'])

# 基本常數
B2_BASE = f"https://f005.backblazeb2.com/file/{config['b2_podcast_prefix']}"
RSS_FILE = config['data_paths']['rss']
COVER_URL = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"

FIXED_DESCRIPTION = """(測試階段)一個適合上班族在最短時間做短線交易策略的節目!
每集節目由涵蓋最新市場數據與 AI 趨勢，專注市值型ETF短線交易策略(因為你沒有無限資金可以東買買西買買，更沒有時間研究個股)！
\n\n讓你在 7 分鐘內快速掌握大盤動向，以獨家研製的短線大盤多空走向，
提供美股每日(SPY,QQQ)的交易策略(喜歡波動小的選SPY/QQQ,波動大的TQQQ/SOXL)。\n\n
提供台股每日(0050或00631L)的交易策略(喜歡波動小的選0050,波動大的00631L)。
\n\n
🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。掌握每日美股、台股、AI工具與新創投資機會！\n\n
📮 主持人：幫幫忙"""

def parse_existing_rss(rss_path):
    existing_entries = []
    if os.path.exists(rss_path):
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find('channel')
            for item in channel.findall('item'):
                entry = {
                    'title': item.find('title').text,
                    'description': item.find('description').text,
                    'enclosure_url': item.find('enclosure').get('url'),
                    'enclosure_length': item.find('enclosure').get('length', '0'),
                    'enclosure_type': item.find('enclosure').get('type', 'audio/mpeg'),
                    'pubDate': item.find('pubDate').text,
                    'guid': item.find('guid').text if item.find('guid') is not None else item.find('enclosure').get('url')
                }
                existing_entries.append(entry)
        except ET.ParseError as e:
            logger.warning(f"RSS 解析錯誤: {e}，重新創建 RSS。")
    return existing_entries

def generate_rss(date, mode, script, audio_url):
    # 初始化 Feed
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.id("https://timhun.github.io/daily-podcast-stk")
    fg.title("幫幫忙說AI投資")
    fg.author({"name": "幫幫忙AI投資腦", "email": "tim.oneway@gmail.com"})
    fg.link(href="https://timhun.github.io/daily-podcast-stk", rel="alternate")
    fg.language("zh-TW")
    fg.description("掌握美股台股、科技、AI 與投資機會，每日兩集！")
    fg.logo(COVER_URL)
    fg.link(href=f"{B2_BASE}/podcast.xml", rel="self")
    fg.podcast.itunes_category("Business", "Investing")
    fg.podcast.itunes_image(COVER_URL)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("幫幫忙AI投資腦")
    fg.podcast.itunes_owner(name="幫幫忙AI投資腦", email="tim.oneway@gmail.com")

    # 加入歷史集數
    existing_entries = parse_existing_rss(RSS_FILE)
    for entry in existing_entries:
        fe = fg.add_entry()
        fe.title(entry['title'])
        fe.description(entry['description'])
        fe.enclosure(entry['enclosure_url'], entry['enclosure_length'], entry['enclosure_type'])
        fe.pubDate(entry['pubDate'])
        fe.guid(entry['guid'], permalink=True)

    # 查找最新集數資料夾
    episodes_dir = config['data_paths']['podcast']
    folder = f"{date}_{mode}"
    base_path = os.path.join(episodes_dir, folder)
    audio_filename = f"daily-podcast-stk-{date}_{mode}.mp3"
    audio = os.path.join(base_path, audio_filename)

    if not os.path.exists(audio):
        logger.error(f"⚠️ 找不到音頻檔案：{audio}")
        raise FileNotFoundError(f"⚠️ 找不到音頻檔案：{audio}")

    # 提取音頻時長
    try:
        mp3 = MP3(audio)
        duration = int(mp3.info.length)
    except Exception as e:
        logger.warning(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    # 設置發布日期
    tz = pytz.timezone("Asia/Taipei")
    pub_date = tz.localize(datetime.datetime.strptime(date, "%Y%m%d"))
    title = f"幫幫忙每日投資快報 - {'台股' if mode == 'tw' else '美股'}（{date}_{mode}）"

    # 使用腳本作為描述
    full_description = FIXED_DESCRIPTION + script[:200] + "..." if script else FIXED_DESCRIPTION

    # 新增集數
    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(title)
    fe.description(full_description)
    fe.content(full_description, type="CDATA")
    fe.enclosure(audio_url, str(os.path.getsize(audio)), "audio/mpeg")
    fe.pubDate(pub_date)
    if duration:
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))
    fe.podcast.itunes_summary(full_description[:500])
    #fe.podcast.itunes_keywords("投資, AI, 美股, 台股, ETF")

    # 輸出 RSS
    try:
        os.makedirs(os.path.dirname(RSS_FILE), exist_ok=True)
        fg.rss_file(RSS_FILE)
        logger.info(f"✅ 已產生 RSS Feed：{RSS_FILE}")
        rss_url = upload_rss(RSS_FILE)
        logger.info(f"RSS 上傳至 B2: {rss_url}")
        notify_slack(date, mode, audio_url)
    except Exception as e:
        logger.error(f"⚠️ 產生 RSS 檔案失敗: {e}")
        raise IOError(f"⚠️ 產生 RSS 檔案失敗: {e}")

def notify_slack(date, mode, audio_url):
    try:
        client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        message = f"New {mode.upper()} podcast episode for {date} is ready! Audio: {audio_url}"
        client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
        logger.info(f"已發送 Slack 通知，{mode} 版 {date} 集數")
        print(f"已發送 Slack 通知，{mode} 版 {date} 集數")
    
    except Exception as e:
        logger.error(f"Slack 通知失敗：{str(e)}")
        raise

if __name__ == "__main__":
    date = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")
    mode = os.getenv("PODCAST_MODE", "tw").lower()
    script_path = f"{config['data_paths']['podcast']}/{date}_{mode}/daily-podcast-stk-{date}_{mode}.txt"
    audio_url = f"{B2_BASE}/daily-podcast-stk-{date}_{mode}.mp3"
    with open(script_path, 'r', encoding='utf-8') as f:
        script = f.read().strip()
    generate_rss(date, mode, script, audio_url)
