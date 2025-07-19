import os
import datetime
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3

# 設定參數
rss_output_path = "docs/rss/podcast.xml"
base_audio_url = "https://daily-podcast-stk.s3.us-east-005.backblazeb2.com"

# 建立 Feed
fg = FeedGenerator()
fg.load_extension('podcast')  # for itunes
fg.id("https://timhun.github.io/daily-podcast-stk/rss/podcast.xml")
fg.title("幫幫忙說財經科技投資")
fg.author({'name': '幫幫忙', 'email': 'tim.oneway@gmail.com'})
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.link(href="https://timhun.github.io/daily-podcast-stk/", rel="alternate")
fg.language("zh-tw")
fg.description("每日更新的美股財經、科技、AI 投資 podcast，7 分鐘掌握市場趨勢。")
fg.logo("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_category('Business', 'Investing')
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_author('幫幫忙')
fg.podcast.itunes_owner(name='幫幫忙', email='tim.oneway@gmail.com')
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")

# 掃描每日目錄
podcast_root = "docs/podcast"
if not os.path.isdir(podcast_root):
    raise FileNotFoundError("找不到 docs/podcast 目錄")

for folder in sorted(os.listdir(podcast_root), reverse=True):
    folder_path = os.path.join(podcast_root, folder)
    audio_path = os.path.join(folder_path, "audio.mp3")
    script_path = os.path.join(folder_path, "script.txt")
    if not os.path.isfile(audio_path) or not os.path.isfile(script_path):
        continue

    try:
        audio = MP3(audio_path)
        duration_secs = int(audio.info.length)
        minutes = duration_secs // 60
        seconds = duration_secs % 60
        duration_str = f"{minutes}:{seconds:02d}"
    except Exception as e:
        print(f"⚠️ 無法讀取 mp3 時長：{e}")
        duration_str = "7:00"

    with open(script_path, "r", encoding="utf-8") as f:
        script = f.read()

    audio_url = f"{base_audio_url}/daily-podcast-stk-{folder}.mp3"
    fe = fg.add_entry()
    fe.id(audio_url)
    fe.title(f"每日投資播報 - {folder}")
    fe.description(script[:200] + "…")
    fe.content(script, type='text')
    fe.enclosure(audio_url, str(os.path.getsize(audio_path)), "audio/mpeg")
    pub_date = datetime.datetime.strptime(folder, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    fe.pubDate(pub_date)
    fe.podcast.itunes_duration(duration_str)

# 寫入 RSS
os.makedirs(os.path.dirname(rss_output_path), exist_ok=True)
fg.rss_file(rss_output_path)
print(f"✅ 成功產生 RSS feed：{rss_output_path}")
