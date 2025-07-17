import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime

fg = FeedGenerator()
fg.load_extension('podcast')

fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")

# 掃描 docs/podcast/YYYYMMDD/audio.mp3
podcast_root = "docs/podcast"
date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)

for d in date_dirs:
    audio_path = f"{podcast_root}/{d}/audio.mp3"
    if os.path.exists(audio_path):
        pub_date = datetime.strptime(d, "%Y%m%d")
        url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"
        file_size = os.path.getsize(audio_path)

        fe = fg.add_entry()
        fe.title(f"每日播報：{pub_date.strftime('%Y/%m/%d')}")
        fe.pubDate(pub_date)
        fe.description("今天的財經科技投資重點播報")
        fe.enclosure(url, file_size, "audio/mpeg")

# 輸出 RSS
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新，含所有歷史集數")