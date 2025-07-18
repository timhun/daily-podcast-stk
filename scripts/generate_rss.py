import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from opencc import OpenCC

# 初始化轉換器（簡轉繁）
cc = OpenCC('s2t')

# 建立 RSS Feed
fg = FeedGenerator()
fg.load_extension('podcast')
fg.language("zh-TW")
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self", type="application/rss+xml")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_explicit("no")

# 掃描日期資料夾（依照倒序）
podcast_root = "docs/podcast"
date_dirs = []
if os.path.exists(podcast_root):
    date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)

# 加入每一集
for d in date_dirs:
    local_script_path = f"{podcast_root}/{d}/script.txt"
    local_audio_path = f"{podcast_root}/{d}/audio.mp3"
    archive_url_path = f"podcast/{d}/archive_audio_url.txt"

    if not os.path.exists(local_audio_path) or not os.path.exists(local_script_path):
        continue

    # 發佈日期
    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)

    # 取得 script.txt 內容（轉成繁體）
    with open(local_script_path, "r", encoding="utf-8") as f:
        script_text = cc.convert(f.read().strip())

    # 擷取第一行當作主題摘要
    summary_line = script_text.splitlines()[0].strip()
    summary_line = cc.convert(summary_line)

    # 音檔連結（來自 archive.org）
    mp3_url_path = f"podcast/{d}/archive_audio_url.txt"
    if not os.path.exists(mp3_url_path):
        continue
    with open(mp3_url_path, "r") as f:
        mp3_url = f.read().strip()

    file_size = os.path.getsize(local_audio_path)

    # 建立一個 RSS item
    fe = fg.add_entry()
    fe.title(f"{summary_line}")
    fe.pubDate(pub_date)
    fe.description(script_text)
    fe.enclosure(mp3_url, file_size, "audio/mpeg")
    fe.guid(mp3_url, permalink=True)

    # 加上 itunes:duration（以秒計算）
    duration_sec = int(os.path.getsize(local_audio_path) / 16000)  # 粗略估計 (128kbps)
    minutes = duration_sec // 60
    seconds = duration_sec % 60
    fe.podcast.itunes_duration(f"{minutes}:{seconds:02d}")
    fe.podcast.itunes_explicit("no")

# 輸出 RSS 檔
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")

print("✅ RSS feed 已更新（使用 archive.org mp3）")
