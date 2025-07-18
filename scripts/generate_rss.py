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
fg.author({'name': '幫幫忙'})
fg.image(url="https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

podcast_root = "docs/podcast"
date_dirs = sorted(
    [d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)],
    reverse=True
)

for d in date_dirs:
    folder = f"{podcast_root}/{d}"
    audio_url_path = os.path.join(folder, "b2_audio_url.txt")
    script_path = os.path.join(folder, "script.txt")
    audio_file_path = os.path.join(folder, "audio.mp3")

    if not os.path.exists(audio_url_path) or not os.path.exists(audio_file_path):
        continue

    with open(audio_url_path, "r") as f:
        audio_url = f.read().strip()

    with open(script_path, "r", encoding="utf-8") as f:
        script = f.read().strip()

    file_size = os.path.getsize(audio_file_path)
    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)

    title_line = script.splitlines()[0][:60] if script else f"每日播報：{d}"

    fe = fg.add_entry()
    fe.title(title_line)
    fe.pubDate(pub_date)
    fe.description(script)
    fe.enclosure(audio_url, file_size, "audio/mpeg")

os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新")