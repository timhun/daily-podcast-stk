import os
import datetime
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3

# 設定基本參數
base_url = "https://f005.backblazeb2.com/file/daily-podcast-stk"
rss_path = "docs/rss/podcast.xml"
audio_dir = "docs/podcast"
cover_url = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"

# 建立 RSS Feed
fg = FeedGenerator()
fg.load_extension('podcast')

# ➤ 必要欄位
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/", rel="alternate")
fg.description("每日 7 分鐘幫你掌握財經、科技、AI、投資新知。")
fg.language("zh-tw")
fg.pubDate(datetime.datetime.now(datetime.UTC))

# ➤ iTunes 專用欄位
fg.generator("GitHub Actions + Kimi + EdgeTTS")
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_owner(name="幫幫忙", email="timhun@gmail.com")
fg.podcast.itunes_image(cover_url)
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# ➤ 加上 <atom:link>
fg._feed.attrib["xmlns:atom"] = "http://www.w3.org/2005/Atom"
fg._feed.append(fg._make_element("atom:link", {
    "href": "https://timhun.github.io/daily-podcast-stk/rss/podcast.xml",
    "rel": "self",
    "type": "application/rss+xml"
}))

# 逐集加入
dates = sorted(os.listdir(audio_dir), reverse=True)
for date_str in dates:
    episode_path = os.path.join(audio_dir, date_str)
    audio_path = os.path.join(episode_path, "audio.mp3")
    script_path = os.path.join(episode_path, "script.txt")

    if not os.path.exists(audio_path) or not os.path.exists(script_path):
        continue

    # 擷取 <title> 與 <description>
    with open(script_path, encoding="utf-8") as f:
        content = f.read().strip()
    title = content.split("\n")[0][:50]
    description = content[:300]

    # 擷取 duration
    audio = MP3(audio_path)
    duration_seconds = int(audio.info.length)
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    duration_str = f"{minutes}:{seconds:02d}"

    fe = fg.add_entry()
    fe.title(title)
    fe.description(description)
    fe.link(href=f"{base_url}/daily-podcast-stk-{date_str}.mp3")
    fe.enclosure(f"{base_url}/daily-podcast-stk-{date_str}.mp3", str(os.path.getsize(audio_path)), "audio/mpeg")
    fe.guid(f"{base_url}/daily-podcast-stk-{date_str}.mp3", permalink=False)
    fe.pubDate(datetime.datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=datetime.timezone.utc))
    fe.podcast.itunes_duration(duration_str)
    fe.podcast.itunes_explicit("no")

# 輸出 RSS
os.makedirs(os.path.dirname(rss_path), exist_ok=True)
fg.rss_file(rss_path)
print(f"✅ 已產生 RSS Feed：{rss_path}")

