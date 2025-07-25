import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator

# ===== 基本常數設定 =====
SITE_URL = "https://timhun.github.io/daily-podcast-stk"
B2_BASE = "https://f005.backblazeb2.com/file/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"

PODCAST_MODE = os.getenv("PODCAST_MODE", "us").lower()
RSS_FILE = f"docs/rss/podcast_{PODCAST_MODE}.xml"

FIXED_DESCRIPTION = """掌握每日美股、台股、AI工具與新創投資機會！
每集節目由涵蓋最新市場數據、法人動向與 AI 趨勢，專注市值型ETF短線交易策略！讓你在 7 分鐘內快速掌握財經動態與科技趨勢。

🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。
📮 主持人：幫幫忙"""

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
fg.link(href=f"{SITE_URL}/rss/podcast_{PODCAST_MODE}.xml", rel="self")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_image(COVER_URL)
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_author("幫幫忙AI投資腦")  # Spotify 驗證需要
fg.podcast.itunes_owner(name="幫幫忙AI投資腦", email="tim.oneway@gmail.com")

# ===== 找出符合模式的最新資料夾 =====
episodes_dir = "docs/podcast"
matching_folders = sorted([
    f for f in os.listdir(episodes_dir)
    if os.path.isdir(os.path.join(episodes_dir, f)) and f.endswith(f"_{PODCAST_MODE}")
], reverse=True)

if not matching_folders:
    print(f"⚠️ 找不到符合模式 '{PODCAST_MODE}' 的 podcast 資料夾，RSS 未產生")
    exit(0)

latest_folder = matching_folders[0]
base_path = os.path.join(episodes_dir, latest_folder)
audio = os.path.join(base_path, "audio.mp3")
archive_url_file = os.path.join(base_path, "archive_audio_url.txt")

if os.path.exists(audio) and os.path.exists(archive_url_file):
    with open(archive_url_file, "r") as f:
        audio_url = f.read().strip()

    try:
        mp3 = MP3(audio)
        duration = int(mp3.info.length)
    except Exception as e:
        print(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    tz = pytz.timezone("Asia/Taipei")
    pub_date = tz.localize(datetime.datetime.strptime(latest_folder.split("_")[0], "%Y%m%d"))
    title = f"幫幫忙每日投資快報 - {'美股' if PODCAST_MODE == 'us' else '台股'}（{latest_folder}）"

    # === 摘要處理區塊 ===
    summary_path = os.path.join(base_path, "summary.txt")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read().strip()
        full_description = f"{FIXED_DESCRIPTION}\n\n🎯 今日摘要：{summary_text}"
    else:
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
    os.makedirs(os.path.dirname(RSS_FILE), exist_ok=True)
    fg.rss_file(RSS_FILE)
    print(f"✅ 已產生 RSS Feed：{RSS_FILE}")
else:
    print(f"⚠️ 缺少必要檔案，無法產生 RSS：{audio}, {archive_url_file}")
