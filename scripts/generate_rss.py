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
fg.author({"name": "幫幫忙"})
fg._feed.attrib['xmlns:itunes'] = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
fg._feed.attrib['xmlns:atom'] = 'http://www.w3.org/2005/Atom'

fg.itunes_category("Business", "Investing")
fg.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.itunes_explicit("no")

podcast_root = "docs/podcast"
date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)

for d in date_dirs:
    base_path = os.path.join(podcast_root, d)
    script_path = os.path.join(base_path, "script.txt")
    audio_url_path = os.path.join(base_path, "archive_audio_url.txt")

    if not os.path.exists(audio_url_path):
        continue

    with open(audio_url_path, "r") as f:
        audio_url = f.read().strip()

    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
    title_line = "(未命名)"
    script_text = "(未提供逐字稿)"

    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()
            match = re.search(r'第[一二三四五六七八九十0-9]+段[:：]?\s*(.+)', script_text)
            if match:
                title_line = match.group(1).strip()
            else:
                title_line = script_text.strip().split("\n")[0][:60]

    fe = fg.add_entry()
    fe.title(f"{d}｜{title_line}")
    fe.description(script_text[:1000])
    fe.pubDate(pub_date)
    fe.enclosure(audio_url, 0, "audio/mpeg")

os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已產生（只使用 archive.org 音訊）")
