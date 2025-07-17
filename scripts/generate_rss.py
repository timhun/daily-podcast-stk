import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

fg = FeedGenerator()
fg.load_extension('podcast')

fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")

podcast_root = "docs/podcast"
date_dirs = []
if os.path.exists(podcast_root):
    date_dirs = sorted(
        [d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)],
        reverse=True
    )

for d in date_dirs:
    audio_path = f"{podcast_root}/{d}/audio.mp3"
    script_path = f"{podcast_root}/{d}/script.txt"
    if os.path.exists(audio_path):
        pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
        url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"
        file_size = os.path.getsize(audio_path)

        # 讀取逐字稿
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read().strip()
        else:
            script_text = "(未提供逐字稿)"

        # 自動摘要作為標題（取前 1～2 行）
        script_lines = [line.strip() for line in script_text.splitlines() if line.strip()]
        if script_lines:
            summary_line = script_lines[0]
            if len(script_lines) > 1:
                summary_line += " " + script_lines[1]
            summary_line = summary_line[:80]  # 最多 80 字
        else:
            summary_line = "每日財經科技AI投資快報"

        # RSS 集數項目
        fe = fg.add_entry()
        fe.title(f"{pub_date.strftime('%Y/%m/%d')}｜{summary_line}")
        fe.pubDate(pub_date)
        fe.description(script_text)
        fe.enclosure(url, file_size, "audio/mpeg")

# 輸出 RSS
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新，含主題摘要與逐字稿")