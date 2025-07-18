import os
import re
import hashlib
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from mutagen.mp3 import MP3

author_name = "幫幫忙"
author_email = "tim.oneway@gmail.com"  # ⚠ 請改成你能收信的 email

fg = FeedGenerator()
fg.load_extension('podcast')

# 基本資訊
fg.title("幫幫忙說財經科技投資")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.language("zh-TW")

# iTunes 設定
fg.podcast.itunes_author(author_name)
fg.podcast.itunes_owner(author_name, author_email)
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_category("Business", "Investing")

# Atom namespace
fg._feed.attrib['xmlns:atom'] = 'http://www.w3.org/2005/Atom'
fg.atom_link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self", type="application/rss+xml")

# podcast 集數
podcast_root = "docs/podcast"
if not os.path.exists(podcast_root):
    raise FileNotFoundError("找不到 podcast 目錄")

date_dirs = sorted(
    [d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)],
    reverse=True
)

for d in date_dirs:
    mp3_path = f"{podcast_root}/{d}/audio.mp3"
    script_path = f"{podcast_root}/{d}/script.txt"
    if not os.path.exists(mp3_path):
        continue

    # 時間與標題
    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
    title = f"每日播報：{pub_date.strftime('%Y/%m/%d')}"

    # 長度與檔案資訊
    mp3 = MP3(mp3_path)
    duration = int(mp3.info.length)
    file_size = os.path.getsize(mp3_path)
    url = f"https://f005.backblazeb2.com/file/daily-podcast-stk/daily-podcast-stk-{d}.mp3"

    # script.txt 讀取
    description = "(未提供逐字稿)"
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            description = f.read().strip()

    # 產生 guid
    guid = hashlib.md5(url.encode("utf-8")).hexdigest()

    # feed entry
    fe = fg.add_entry()
    fe.title(title)
    fe.description(description)
    fe.enclosure(url, str(file_size), "audio/mpeg")
    fe.pubDate(pub_date)
    fe.guid(guid, isPermaLink=False)
    fe.podcast.itunes_duration(str(duration))
    fe.link(href=url)

# 輸出
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ 已更新 RSS feed（含 Apple Podcast 與 Spotify 相容欄位）")
