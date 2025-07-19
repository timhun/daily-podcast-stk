import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator

# RSS 基本設定
SITE_URL = "https://timhun.github.io/daily-podcast-stk"
AUDIO_BASE_URL = "https://f005.backblazeb2.com/file/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"
RSS_FILE_PATH = "docs/rss/podcast.xml"

# 建立 FeedGenerator
fg = FeedGenerator()
fg.load_extension('podcast')  # 支援 itunes namespace
fg.id(SITE_URL)
fg.title("幫幫忙說財經科技投資")
fg.author({'name': '幫幫忙', 'email': 'tim.oneway@gmail.com'})
fg.link(href=SITE_URL, rel='alternate')
fg.language('zh-TW')
fg.description("用台灣專業大叔口吻，陪你掌握財經、科技、AI、投資，輕鬆又有料的早晨 podcast！")
fg.logo(COVER_URL)
fg.link(href=f"{SITE_URL}/rss/podcast.xml", rel='self')
fg.podcast.itunes_category('Business', 'Investing')
fg.podcast.itunes_image(COVER_URL)
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_owner(name='幫幫忙', email='tim.oneway@gmail.com')

# 掃描音檔資料夾
episodes_dir = "docs/podcast"
folders = sorted(
    [f for f in os.listdir(episodes_dir) if os.path.isdir(os.path.join(episodes_dir, f))],
    reverse=True
)

for folder in folders:
    folder_path = os.path.join(episodes_dir, folder)
    audio_path = os.path.join(folder_path, "audio.mp3")
    script_path = os.path.join(folder_path, "script.txt")

    if not os.path.exists(audio_path) or not os.path.exists(script_path):
        continue

    try:
        audio = MP3(audio_path)
        duration = int(audio.info.length)
    except Exception as e:
        print(f"⚠️ 無法讀取 mp3 時長：{e}")
        duration = None

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            description = f.read().strip()
    except Exception as e:
        print(f"⚠️ 無法讀取逐字稿：{e}")
        description = "本日無法取得內容"

    audio_url = f"{AUDIO_BASE_URL}/daily-podcast-stk-{folder}.mp3"

    try:
        fe = fg.add_entry()
        fe.id(audio_url)
        fe.guid(audio_url, permalink=True)
        fe.title(f"幫幫忙每日投資快報 - {folder}")
        fe.description(description)
        fe.podcast.itunes_summary(description)
        fe.podcast.itunes_subtitle(description.splitlines()[0] if description else "幫幫忙每日投資快報")
        fe.enclosure(audio_url, str(os.path.getsize(audio_path)), 'audio/mpeg')
        pub_dt = datetime.datetime.strptime(folder, "%Y%m%d").replace(tzinfo=pytz.UTC)
        fe.pubDate(pub_dt)
        fe.podcast.itunes_explicit("no")
        if duration:
            fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))
    except Exception as e:
        print(f"⚠️ 發生錯誤，跳過 {folder}：{e}")
        continue

# 儲存 RSS 檔案
os.makedirs(os.path.dirname(RSS_FILE_PATH), exist_ok=True)
fg.rss_file(RSS_FILE_PATH)
print("✅ 成功產生 RSS feed：", RSS_FILE_PATH)