import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator

SITE_URL = "https://timhun.github.io/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"
RSS_FILE_PATH = "docs/rss/podcast.xml"

# 建立 RSS Feed
fg = FeedGenerator()
fg.load_extension('podcast')
fg.id(SITE_URL)
fg.title("幫幫忙說財經科技投資")
fg.author({'name': '幫幫忙', 'email': 'tim.oneway@gmail.com'})
fg.link(href=SITE_URL, rel='alternate')
fg.language('zh-TW')
fg.description("陪你掌握財經、科技、AI、投資，輕鬆又有料的早晨 podcast！")
fg.logo(COVER_URL)
fg.link(href=f"{SITE_URL}/rss/podcast.xml", rel='self')
fg.podcast.itunes_category('Business', 'Investing')
fg.podcast.itunes_image(COVER_URL)
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_owner(name='幫幫忙', email='tim.oneway@gmail.com')

# 掃描所有目錄（如 docs/podcast/20250720-us）
episodes_dir = "docs/podcast"
folders = sorted(
    [f for f in os.listdir(episodes_dir) if os.path.isdir(os.path.join(episodes_dir, f))],
    reverse=True
)

for folder in folders:
    folder_path = os.path.join(episodes_dir, folder)
    audio_path = os.path.join(folder_path, "audio.mp3")
    script_path = os.path.join(folder_path, "script.txt")
    audio_url_file = os.path.join(folder_path, "archive_audio_url.txt")

    if not os.path.exists(audio_path) or not os.path.exists(script_path):
        continue

    # 檢查 audio_url
    if os.path.exists(audio_url_file):
        with open(audio_url_file, "r") as f:
            audio_url = f.read().strip()
    else:
        # fallback
        audio_url = f"https://f005.backblazeb2.com/file/daily-podcast-stk/daily-podcast-stk-{folder}.mp3"

    try:
        audio = MP3(audio_path)
        duration = int(audio.info.length)
    except Exception as e:
        print(f"⚠️ 讀取時長失敗：{e}")
        duration = None

    with open(script_path, "r", encoding="utf-8") as f:
        description = f.read().strip()

    # 日期與 mode
    if "-" in folder:
        date_part, mode = folder.split("-")
        title_suffix = "美股快報" if mode == "us" else "台股午後"
    else:
        date_part = folder
        title_suffix = "每日快報"

    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(f"幫幫忙 {date_part} - {title_suffix}")
    fe.description(description)
    fe.enclosure(audio_url, str(os.path.getsize(audio_path)), 'audio/mpeg')
    fe.pubDate(datetime.datetime.strptime(date_part, "%Y%m%d").replace(tzinfo=pytz.UTC))
    if duration:
        import datetime as dt
        fe.podcast.itunes_duration(str(dt.timedelta(seconds=duration)))

# 儲存 RSS
os.makedirs(os.path.dirname(RSS_FILE_PATH), exist_ok=True)
fg.rss_file(RSS_FILE_PATH)
print("✅ RSS 已更新：", RSS_FILE_PATH)
