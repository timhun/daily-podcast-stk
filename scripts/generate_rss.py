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
fg.image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

# RSS 強制欄位
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

root = "docs/podcast"
date_dirs = sorted(
    [d for d in os.listdir(root) if re.match(r'\d{8}', d)],
    reverse=True
)

for d in date_dirs:
    folder = f"{root}/{d}"
    script_file = f"{folder}/script.txt"
    audio_file = f"{folder}/audio.mp3"
    archive_url_file = f"{folder}/archive_audio_url.txt"

    if os.path.exists(audio_file):
        pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
        file_size = os.path.getsize(audio_file)

        # 標題與說明
        script = "(未提供逐字稿)"
        title_text = f"每日播報：{pub_date.strftime('%Y/%m/%d')}"
        if os.path.exists(script_file):
            with open(script_file, encoding="utf-8") as f:
                script = f.read().strip()
            # 嘗試從前兩行抓出主題當作標題
            lines = script.splitlines()
            if len(lines) >= 1:
                title_text = lines[0][:50]

        # 音訊網址（使用 archive.org 優先）
        if os.path.exists(archive_url_file):
            with open(archive_url_file) as f:
                audio_url = f.read().strip()
        else:
            audio_url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"

        fe = fg.add_entry()
        fe.title(title_text)
        fe.description(script)
        fe.pubDate(pub_date)
        fe.enclosure(audio_url, file_size, "audio/mpeg")

# 輸出 RSS
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ 已產生 RSS feed：docs/rss/podcast.xml")
