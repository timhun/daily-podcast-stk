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

# 掃描 docs/podcast/YYYYMMDD 資料夾
podcast_root = "docs/podcast"
date_dirs = []

# ✅ 防止第一次執行時爆錯
if os.path.exists(podcast_root):
    date_dirs = sorted(
        [d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)],
        reverse=True
    )

# 逐集加入 <item>
for d in date_dirs:
    audio_path = f"{podcast_root}/{d}/audio.mp3"
    script_path = f"podcast/{d}/script.txt"
    if os.path.exists(audio_path):
        pub_date = datetime.strptime(d, "%Y%m%d")
        url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"
        file_size = os.path.getsize(audio_path)

        # 讀取逐字稿
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read().strip()
        else:
            script_text = "(未提供逐字稿)"

        fe = fg.add_entry()
        fe.title(f"每日播報：{pub_date.strftime('%Y/%m/%d')}")
        fe.pubDate(pub_date)
        fe.description(script_text)
        fe.enclosure(url, file_size, "audio/mpeg")

# 輸出 RSS 到 docs/rss/podcast.xml
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")

print("✅ RSS feed 已更新，含歷史集數與逐字稿")