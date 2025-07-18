import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

fg = FeedGenerator()
fg.load_extension('podcast')

# 加入 namespace 擴充（iTunes / Atom / Podcast）
fg._feed.attrib.update({
    'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'xmlns:atom': 'http://www.w3.org/2005/Atom',
    'xmlns:podcast': 'https://podcastindex.org/namespace/1.0'
})

# Feed 主要設定
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.author({'name': '幫幫忙'})
fg.logo("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# 來源資料目錄
podcast_root = "docs/podcast"
date_dirs = []
if os.path.exists(podcast_root):
    date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)

for d in date_dirs:
    local_dir = os.path.join(podcast_root, d)
    audio_path = os.path.join(local_dir, "audio.mp3")
    script_path = os.path.join(local_dir, "script.txt")
    archive_url_path = os.path.join(local_dir, "archive_audio_url.txt")

    if os.path.exists(audio_path):
        # 發佈時間
        pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)

        # 使用 archive.org 的音檔網址（若有）
        if os.path.exists(archive_url_path):
            with open(archive_url_path, "r") as f:
                audio_url = f.read().strip()
        else:
            audio_url = f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/audio.mp3"

        # 檔案大小
        file_size = os.path.getsize(audio_path)

        # 逐字稿文字
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read().strip()
        else:
            script_text = "（無逐字稿）"

        # 擷取標題摘要：取前 1 行或前 30 字
        title_line = script_text.splitlines()[0] if script_text else f"每日播報：{d}"
        title = f"{d}｜{title_line[:30]}"

        # 建立項目
        fe = fg.add_entry()
        fe.id(f"tag:daily-podcast-stk,{d}")
        fe.title(title)
        fe.pubDate(pub_date)
        fe.description(script_text)
        fe.enclosure(audio_url, file_size, "audio/mpeg")

        # 可選項目
        fe.link(href=audio_url)
        fe.podcast.itunes_duration("00:12:00")
        fe.podcast.itunes_explicit("no")
        fe.podcast.transcript(f"https://timhun.github.io/daily-podcast-stk/podcast/{d}/script.txt", type="text/plain")

# 輸出 RSS XML
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")

print("✅ RSS feed 已產生，集數：", len(date_dirs))
