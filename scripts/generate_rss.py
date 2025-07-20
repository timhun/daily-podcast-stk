import os
import datetime
import pytz
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator

SITE_URL = "https://timhun.github.io/daily-podcast-stk"
B2_BASE = "https://f005.backblazeb2.com/file/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"
RSS_FILE = "docs/rss/podcast.xml"

fg = FeedGenerator()
fg.load_extension("podcast")
fg.id(SITE_URL)
fg.title("幫幫忙說財經科技投資")
fg.author({"name": "幫幫忙", "email": "tim.oneway@gmail.com"})
fg.link(href=SITE_URL, rel="alternate")
fg.language("zh-TW")
fg.description("掌握美股台股、科技、AI 與投資機會，每日兩集！")
fg.logo(COVER_URL)
fg.link(href=f"{SITE_URL}/rss/podcast.xml", rel="self")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_image(COVER_URL)
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_owner(name="幫幫忙", email="tim.oneway@gmail.com")

episodes_dir = "docs/podcast"
folders = sorted([
    f for f in os.listdir(episodes_dir)
    if os.path.isdir(os.path.join(episodes_dir, f)) and "_" in f
], reverse=True)

for folder in folders:
    base_path = os.path.join(episodes_dir, folder)
    audio = os.path.join(base_path, "audio.mp3")
    script = os.path.join(base_path, "script.txt")
    archive_url_file = os.path.join(base_path, "archive_audio_url.txt")

    if not (os.path.exists(audio) and os.path.exists(script) and os.path.exists(archive_url_file)):
        continue

    with open(archive_url_file, "r") as f:
        audio_url = f.read().strip()

    with open(script, "r", encoding="utf-8") as f:
        description = f.read().strip()

    try:
        mp3 = MP3(audio)
        duration = int(mp3.info.length)
    except Exception as e:
        print(f"⚠️ 讀取 mp3 時長失敗：{e}")
        duration = None

    pub_date = datetime.datetime.strptime(folder.split("_")[0], "%Y%m%d").replace(tzinfo=pytz.UTC)
    mode = folder.split("_")[1].upper()
    title = f"幫幫忙每日投資快報 - {'美股' if mode == 'US' else '台股'}（{folder}）"

    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(title)
    fe.description(description)
    fe.enclosure(audio_url, str(os.path.getsize(audio)), "audio/mpeg")
    fe.pubDate(pub_date)
    if duration:
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration)))

os.makedirs(os.path.dirname(RSS_FILE), exist_ok=True)
fg.rss_file(RSS_FILE)
print("✅ 已產生 RSS Feed：", RSS_FILE)