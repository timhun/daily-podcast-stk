import os
import re
import datetime
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3, HeaderNotFoundError

base_url = "https://f005.backblazeb2.com/file/daily-podcast-stk"
rss_output = "docs/rss/podcast.xml"
cover_image_url = "https://timhun.github.io/daily-podcast-stk/img/cover.jpg"
email = "tim.oneway@email.com"  # ✅ 請改為你的 Apple/Spotify 驗證 email

fg = FeedGenerator()
fg.load_extension('podcast')
fg.id("https://timhun.github.io/daily-podcast-stk/rss/podcast.xml")
fg.title("幫幫忙說財經科技投資")
fg.author({"name": "幫幫忙", "email": email})
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.link(href="https://timhun.github.io/daily-podcast-stk/", rel="alternate")
fg.logo(cover_image_url)
fg.image(cover_image_url)
fg.language("zh-TW")
fg.description("每日 AI 自動播報：財經、科技、投資、AI 工具，一次掌握")
fg.podcast.itunes_category("Business", "Investing")
fg.podcast.itunes_explicit("no")

# 依序加入每一集
podcast_root = "docs/podcast"
for folder in sorted(os.listdir(podcast_root), reverse=True):
    folder_path = os.path.join(podcast_root, folder)
    if not os.path.isdir(folder_path):
        continue

    script_path = os.path.join(folder_path, "script.txt")
    audio_path = os.path.join(folder_path, "audio.mp3")
    if not os.path.exists(script_path) or not os.path.exists(audio_path):
        print(f"⚠️ 缺少 script 或 mp3：{folder}")
        continue

    # 嘗試解析 MP3 音訊長度
    try:
        audio = MP3(audio_path)
        duration_sec = int(audio.info.length)
    except HeaderNotFoundError:
        print(f"⚠️ 無法解析 MP3 音訊：{audio_path}，跳過此集")
        continue

    # 讀取逐字稿前幾行作為標題與摘要
    with open(script_path, encoding="utf-8") as f:
        lines = f.readlines()
    lines = [line.strip() for line in lines if line.strip()]
    title = re.sub(r"[「」\"\']", "", lines[0])[:50] if lines else f"每日播報 - {folder}"
    description = " ".join(lines[1:4])[:150] if len(lines) >= 2 else "自動播報財經科技內容"

    # 組成 enclosure URL
    mp3_url = f"{base_url}/daily-podcast-stk-{folder}.mp3"

    fe = fg.add_entry()
    fe.id(mp3_url)
    fe.title(title)
    fe.description(description)
    fe.pubDate(datetime.datetime.strptime(folder, "%Y%m%d"))
    fe.enclosure(mp3_url, 0, "audio/mpeg")
    fe.podcast.itunes_duration(str(datetime.timedelta(seconds=duration_sec)))

# 輸出 RSS 檔案
os.makedirs(os.path.dirname(rss_output), exist_ok=True)
fg.rss_file(rss_output, pretty=True)
print(f"✅ RSS 產生完成：{rss_output}")
