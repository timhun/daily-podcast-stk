import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from mutagen.mp3 import MP3

output_path = "docs/rss/podcast.xml"
rss_url = "https://timhun.github.io/daily-podcast-stk/rss/podcast.xml"
cover_url = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"

fg = FeedGenerator()
fg.load_extension('podcast')

# 頻道基本資訊
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk", rel="alternate")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.author({"name": "幫幫忙", "email": "no-reply@timhun.github.io"})
fg.image(cover_url)

# Apple 專屬欄位
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_summary("每天更新的財經、科技、AI、投資語音節目，由幫幫忙主持。")
fg.podcast.itunes_owner(name="幫幫忙", email="no-reply@timhun.github.io")
fg.podcast.itunes_image(cover_url)
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# 建立集數
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

        # 取得語音時長
        try:
            audio = MP3(audio_path)
            duration_sec = int(audio.info.length)
            h = duration_sec // 3600
            m = (duration_sec % 3600) // 60
            s = duration_sec % 60
            duration_str = f"{h:02}:{m:02}:{s:02}" if h > 0 else f"{m:02}:{s:02}"
        except Exception:
            duration_str = None

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
        if duration_str:
            fe.podcast.itunes_duration(duration_str)

# 儲存 XML 檔案
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file(output_path)

# ✅ 後處理：插入 atom:link 與 xmlns:atom
with open(output_path, "r", encoding="utf-8") as f:
    rss = f.read()

rss = rss.replace(
    '<rss version="2.0"',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"'
)
rss = rss.replace(
    "<channel>",
    f"<channel>\n  <atom:link href=\"{rss_url}\" rel=\"self\" type=\"application/rss+xml\" />"
)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(rss)

print("✅ RSS feed 已更新，含 itunes:duration 與 atom:link")
