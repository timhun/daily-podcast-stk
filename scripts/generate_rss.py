import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import mimetypes
import math
from mutagen.mp3 import MP3

fg = FeedGenerator()
fg.load_extension('podcast')

# ✅ Feed 頭資訊
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.author({'name': '幫幫忙'})
fg.image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

# ✅ 支援 Apple 要求的 atom:link
fg._feed.attrib['xmlns:atom'] = 'http://www.w3.org/2005/Atom'
fg.atom_file("docs/rss/podcast.xml")

# ✅ 集數來源目錄
podcast_root = "docs/podcast"
date_dirs = []
if os.path.exists(podcast_root):
    date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)

for d in date_dirs:
    folder = os.path.join(podcast_root, d)
    audio_path = os.path.join(folder, "audio.mp3")
    script_path = os.path.join(folder, "script.txt")
    archive_url_path = os.path.join(folder, "archive_audio_url.txt")

    if not os.path.exists(audio_path):
        continue

    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)

    # ✅ 讀取音訊網址（優先使用 archive.org）
    if os.path.exists(archive_url_path):
        with open(archive_url_path) as f:
            audio_url = f.read().strip()
    else:
        audio_url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"

    # ✅ 讀取逐字稿內容
    if os.path.exists(script_path):
        with open(script_path, encoding="utf-8") as f:
            script_text = f.read().strip()
        title_line = script_text.split("\n")[0].strip()
    else:
        script_text = "(未提供逐字稿)"
        title_line = f"每日播報：{pub_date.strftime('%Y/%m/%d')}"

    # ✅ 檔案大小與時長
    file_size = os.path.getsize(audio_path)
    try:
        audio_info = MP3(audio_path)
        duration_sec = int(audio_info.info.length)
        duration_min = duration_sec // 60
        duration_str = f"{duration_min}:{duration_sec % 60:02d}"
    except:
        duration_str = "12:00"  # fallback 預設

    fe = fg.add_entry()
    fe.title(title_line)
    fe.pubDate(pub_date)
    fe.description(script_text)
    fe.enclosure(audio_url, file_size, "audio/mpeg")
    fe.podcast.itunes_duration(duration_str)
    fe.podcast.itunes_explicit("no")

# ✅ 儲存 RSS XML 檔
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新，含逐字稿、封面與 archive.org 支援")
