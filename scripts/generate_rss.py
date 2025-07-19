import os
import datetime
import pathlib
from mutagen.mp3 import MP3
from feedgen.feed import FeedGenerator

rss_output_path = "docs/rss/podcast.xml"
base_audio_url = "https://f005.backblazeb2.com/file/daily-podcast-stk"

fg = FeedGenerator()
fg.load_extension("podcast")

# 基本資訊
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.language("zh-tw")
fg.description("每天早晨幫你掌握最新的財經、科技與 AI 投資趨勢！")
fg.author(name="幫幫忙", email="podcast@timhun.ai")
fg.itunes_author("幫幫忙")
fg.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.itunes_category("Business", "Investing")
fg.itunes_explicit("no")

# 逐集掃描 docs/podcast/YYYYMMDD/
episodes_root = pathlib.Path("docs/podcast")
for folder in sorted(episodes_root.iterdir(), reverse=True):
    if not folder.is_dir():
        continue
    date_str = folder.name
    audio_path = folder / "audio.mp3"
    script_path = folder / "script.txt"
    if not audio_path.exists() or not script_path.exists():
        continue

    try:
        audio = MP3(audio_path)
        duration_seconds = int(audio.info.length)
        duration_min = duration_seconds // 60
        duration_sec = duration_seconds % 60
        duration_str = f"{duration_min}:{duration_sec:02d}"
    except Exception as e:
        print(f"⚠️ 無法解析音檔 {audio_path}: {e}")
        continue

    with open(script_path, encoding="utf-8") as f:
        description = f.read().strip()

    enclosure_url = f"{base_audio_url}/daily-podcast-stk-{date_str}.mp3"

    fe = fg.add_entry()
    fe.id(f"daily-podcast-stk-{date_str}")
    fe.title(f"每日播報 - {date_str}")
    fe.description(description)
    fe.enclosure(enclosure_url, 0, "audio/mpeg")
    fe.pubDate(datetime.datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=datetime.timezone.utc))
    fe.itunes_duration(duration_str)

# 輸出 RSS
os.makedirs(os.path.dirname(rss_output_path), exist_ok=True)
fg.rss_file(rss_output_path, encoding="utf-8")
print("✅ 已產生 RSS feed 至", rss_output_path)