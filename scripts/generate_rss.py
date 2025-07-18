import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from mutagen.mp3 import MP3

# 初始化 FeedGenerator 並手動設置命名空間
fg = FeedGenerator()
fg.load_extension('podcast')
fg.load_extension('itunes')

# 手動設置 XML 命名空間
fg._feed.attrib['xmlns:atom'] = 'http://www.w3.org/2005/Atom'

# 設定頻道資訊
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://daily-podcast-stk.s3.us-east-005.backblazeb2.com/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")
fg.itunes_author("幫幫忙")
fg.itunes_image("https://daily-podcast-stk.s3.us-east-005.backblazeb2.com/img/cover.jpg")
fg.itunes_explicit("no")

# 手動加入 atom:link 標籤
fg._feed.append(fg._element('atom:link', {
    'href': "https://daily-podcast-stk.s3.us-east-005.backblazeb2.com/rss/podcast.xml",
    'rel': "self",
    'type': "application/rss+xml"
}))

# 掃描每日 podcast 目錄
podcast_root = "docs/podcast"
if os.path.exists(podcast_root):
    date_dirs = sorted([d for d in os.listdir(podcast_root) if re.match(r'\d{8}', d)], reverse=True)
else:
    date_dirs = []

for d in date_dirs:
    audio_path = f"{podcast_root}/{d}/audio.mp3"
    script_path = f"{podcast_root}/{d}/script.txt"

    if not os.path.exists(audio_path):
        continue

    pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
    file_size = os.path.getsize(audio_path)

    # 使用 B2 S3 URL 作為 enclosure
    enclosure_url = f"https://daily-podcast-stk.s3.us-east-005.backblazeb2.com/daily-podcast-stk-{d}.mp3"

    # 擷取逐字稿
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()
    else:
        script_text = "(未提供逐字稿)"

    # 擷取標題
    match = re.search(r'(.+?)[。？！？!?\n]', script_text)
    title = match.group(1).strip() if match else f"每日播報：{d[:4]}/{d[4:6]}/{d[6:]}"

    # 擷取音檔長度
    try:
        audio = MP3(audio_path)
        duration_secs = int(audio.info.length)
        minutes = duration_secs // 60
        seconds = duration_secs % 60
        duration_str = f"{minutes}:{seconds:02d}"
    except Exception:
        duration_str = "7:00"  # fallback

    # 建立 RSS entry
    fe = fg.add_entry()
    fe.title(title)
    fe.pubDate(pub_date)
    fe.description(script_text)
    fe.enclosure(enclosure_url, file_size, "audio/mpeg")
    fe.itunes_duration(duration_str)
    fe.guid(enclosure_url)
    fe.link(href=enclosure_url)
    fe.itunes_explicit("no")

# 輸出 RSS
os.makedirs("docs/rss", exist_ok=True)
fg.rss_file("docs/rss/podcast.xml")
print("✅ RSS feed 已更新，總集數：", len(date_dirs))
