import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from mutagen.mp3 import MP3

# 初始化 feed
fg = FeedGenerator()
fg.load_extension('podcast')

# 設定 Podcast 基本資訊
fg.title("幫幫忙說財經科技投資")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="alternate")
fg.atom_link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.generator("FeedGenerator")
fg.author({"name": "幫幫忙"})

# iTunes 專屬欄位
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_owner(name="幫幫忙", email="your@email.com")  # Spotify 驗證需有 email

# 處理所有音檔資料夾
podcast_root = "docs/podcast"
date_dirs = sorted(
    [d for d in os.listdir(podcast_root) if re.match(r"\d{8}", d)],
    reverse=True
)

for d in date_dirs:
    folder = os.path.join(podcast_root, d)
    audio_path = os.path.join(folder, "audio.mp3")
    script_path = os.path.join(folder, "script.txt")

    if not os.path.exists(audio_path):
        continue

    # 取得檔案資訊
    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
    file_size = os.path.getsize(audio_path)
    audio = MP3(audio_path)
    duration = int(audio.info.length)

    # 取得逐字稿
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script = f.read().strip()
    else:
        script = "本集未提供逐字稿。"

    # 產生 enclosure 連結（Backblaze B2）
    enclosure_url = f"https://f005.backblazeb2.com/file/daily-podcast-stk/daily-podcast-stk-{d}.mp3"

    # 加入 feed 項目
    fe = fg.add_entry()
    fe.title(f"每日播報：{pub_date.strftime('%Y/%m/%d')}")
    fe.pubDate(pub_date)
    fe.description(script)
    fe.enclosure(enclosure_url, str(file_size), "audio/mpeg")
    fe.podcast.itunes_duration(str(duration))

# 輸出 RSS
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 產生完成：docs/rss/podcast.xml")
