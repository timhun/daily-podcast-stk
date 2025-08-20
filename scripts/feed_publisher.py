import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== 基本常數設定 =====
SITE_URL = "https://timhun.github.io/daily-podcast-stk"
B2_BASE = "https://f005.backblazeb2.com/file/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"

PODCAST_MODE = os.getenv("PODCAST_MODE", "tw").lower()
RSS_FILE = f"docs/rss/podcast_{PODCAST_MODE}.xml"

FIXED_DESCRIPTION = """(測試階段)一個適合上班族在最短時間做短線交易策略的節目!
每集節目由涵蓋最新市場數據與 AI 趨勢，專注市值型ETF短線交易策略。
🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。
📮 主持人：幫幫忙
"""

def generate_rss():
    # ===== 初始化 Feed =====
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.id(SITE_URL)
    fg.title("幫幫忙說AI.投資")
    fg.author({"name": "幫幫忙AI投資腦", "email": "tim.oneway@gmail.com"})
    fg.link(href=SITE_URL, rel="alternate")
    fg.language("zh-TW")
    fg.description("掌握美股台股、科技、AI 與投資機會，每日兩集！")
    fg.logo(COVER_URL)
    fg.link(href=RSS_FILE, rel="self")
    fg.podcast.itunes_category("Business", "Investing")
    fg.podcast.itunes_image(COVER_URL)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_author("幫幫忙AI投資腦")
    fg.podcast.itunes_owner(name="幫幫忙AI投資腦", email="tim.oneway@gmail.com")

    # ===== 找出符合模式的最新資料夾 =====
    episodes_dir = "docs/podcast"
    matching_folders = sorted([
        f for f in os.listdir(episodes_dir)
        if os.path.isdir(os.path.join(episodes_dir, f)) and f.endswith(f"_{PODCAST_MODE}")
    ], reverse=True)

    if not matching_folders:
        logger.warning(f"⚠️ 找不到符合模式 '{PODCAST_MODE}' 的 podcast 資料夾，RSS 將跳過")
        return

    latest_folder = matching_folders[0]
    base_path = os.path.join(episodes_dir, latest_folder)
    audio = os.path.join(base_path, "audio.mp3")
    archive_url_file = os.path.join(base_path, "archive_audio_url.txt")

    if not os.path.exists(audio):
        logger.warning(f"⚠️ 找不到 audio.mp3：{audio}，RSS 將跳過此集")
        return
    if not os.path.exists(archive_url_file):
        logger.warning(f"⚠️ 找不到 archive_audio_url.txt：{archive_url_file}，RSS 將跳過此集")
        return

    with open(archive_url_file, "r", encoding="utf-8") as f:
        audio_url = f.read().strip()

    try:
        mp3 = MP3(audio)
        duration = int(mp3.info.length)
    except Exception as e:
        logger.warning(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    tz = pytz.timezone("Asia/Taipei")
    pub_date = tz.localize(datetime.datetime.strptime(latest_folder.split("_")[0], "%Y%m%d"))
    title = f"幫幫忙每日投資快報 - {'台股' if PODCAST_MODE == 'tw' else '美股'}（{latest_folder}）"

    # === 摘要處理區塊 ===
    summary_path = os.path.join(base_path, "summary.txt")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read().strip()
        full_description = f"{FIXED_DESCRIPTION}\n\n🎯 今日摘要：{summary_text}"
    else:
        logger.info("⚠️ 找不到 summary.txt，使用預設描述")
        full_description = FIXED_DESCRIPTION

    # === Feed Entry ===
    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(title)
    fe.description(full_description)
    fe.content(full_description, type="CDATA")
    fe.enclosure(audio_url, str(os.path.getsize(audio)), "audio/mpeg")
    fe.pubDate(pub_date)
    if duration:
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))

    # 輸出 RSS
    try:
        os.makedirs(os.path.dirname(RSS_FILE), exist_ok=True)
        fg.rss_file(RSS_FILE)
        logger.info(f"✅ 已產生 RSS Feed：{RSS_FILE}")
    except Exception as e:
        logger.error(f"⚠️ 產生 RSS 檔案失敗: {e}")
        raise IOError(f"⚠️ 產生 RSS 檔案失敗: {e}")

if __name__ == "__main__":
    generate_rss()