import os
import datetime
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3
from xml.etree import ElementTree as ET

# 設定參數
base_url = "https://f005.backblazeb2.com/file/daily-podcast-stk"
rss_path = "docs/rss/podcast.xml"
audio_dir = "docs/podcast"
cover_url = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"

# 建立 FeedGenerator
fg = FeedGenerator()
fg.load_extension("podcast")

fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/", rel="alternate")
fg.description("每日 7 分鐘幫你掌握財經、科技、AI、投資新知。")
fg.language("zh-tw")
fg.pubDate(datetime.datetime.now(datetime.UTC))

fg.generator("GitHub Actions")
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_owner(name="幫幫忙", email="timhun@gmail.com")
fg.podcast.itunes_image(cover_url)
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# 加入每一集
dates = sorted(os.listdir(audio_dir), reverse=True)
for date_str in dates:
    episode_path = os.path.join(audio_dir, date_str)
    audio_path = os.path.join(episode_path, "audio.mp3")
    script_path = os.path.join(episode_path, "script.txt")

    if not os.path.exists(audio_path) or not os.path.exists(script_path):
        continue

    with open(script_path, encoding="utf-8") as f:
        content = f.read().strip()
    title = content.split("\n")[0][:50]
    description = content[:300]

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

# 儲存為 XML 字串
rss_str = fg.rss_str(pretty=True)
root = ET.fromstring(rss_str)

# 加入 <atom:link>
atom_ns = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", atom_ns)
channel = root.find("channel")
if channel is not None:
    atom_link = ET.Element(f"{{{atom_ns}}}link", {
        "href": "https://timhun.github.io/daily-podcast-stk/rss/podcast.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })
    channel.insert(0, atom_link)

# 儲存到檔案
ET.ElementTree(root).write(rss_path, encoding="utf-8", xml_declaration=True)
print(f"✅ 已產生 RSS Feed：{rss_path}")
