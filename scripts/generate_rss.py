import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

fg = FeedGenerator()
fg.load_extension('podcast')

# 頻道基本資訊
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk", rel="alternate")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.author({"name": "幫幫忙", "email": "no-reply@timhun.github.io"})
fg.image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

# Apple Podcasts 必備欄位
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_summary("每天更新的財經、科技、AI、投資語音節目，由幫幫忙主持。")
fg.podcast.itunes_owner(name="幫幫忙", email="no-reply@timhun.github.io")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# ✅ 兼容方式手動補 atom:link
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self", type="application/rss+xml")
fg._feed.attrib['xmlns:atom'] = 'http://www.w3.org/2005/Atom'  # ⚠ 需使用 _feed

# 歷史集數
podcast_root = "docs/podcast"
date_dirs = sorted(
    [d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)],
    reverse=True
) if os.path.exists(podcast_root) else []

for d in date_dirs:
    audio_path = f"{podcast_root}/{d}/audio.mp3"
    script_path = f"{podcast_root}/{d}/script.txt"
    if os.path.exists(audio_path):
        pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
        url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"
        file_size = os.path.getsize(audio_path)

        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read().strip()
        else:
            script_text = "(未提供逐字稿)"

        lines = [line.strip() for line in script_text.splitlines() if line.strip()]
        if lines:
            summary_line = lines[0] + (" " + lines[1] if len(lines) > 1 else "")
            summary_line = summary_line[:80]
        else:
            summary_line = "每日財經科技AI投資快報"

        fe = fg.add_entry()
        fe.title(f"{pub_date.strftime('%Y/%m/%d')}｜{summary_line}")
        fe.description(script_text)
        fe.pubDate(pub_date)
        fe.enclosure(url, file_size, "audio/mpeg")
        fe.guid(url)

# 輸出 RSS 檔案
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新，支援 Apple Podcasts 所需欄位")
