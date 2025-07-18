import os
import re
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

# ⚙️ 基本設定
B2_BASE_URL = "https://f005.backblazeb2.com/file/daily-podcast-stk"
OUTPUT_PATH = "docs/rss/podcast.xml"
SCRIPT_ROOT = "docs/podcast"

# 建立 RSS Feed
fg = FeedGenerator()
fg.load_extension('podcast')

# Required namespaces
fg.generator("daily-podcast-stk")
fg.language("zh-TW")
fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天更新的財經、科技、AI、投資語音節目")

# iTunes 專用設定
fg.podcast.itunes_author("幫幫忙")
fg.podcast.itunes_explicit("no")
fg.podcast.itunes_image("https://timhun.github.io/daily-podcast-stk/img/cover.jpg")
fg.podcast.itunes_category("Business", "Investing")

# 逐集處理
if os.path.exists(SCRIPT_ROOT):
    date_dirs = sorted(
        [d for d in os.listdir(SCRIPT_ROOT) if re.match(r'\d{8}', d)],
        reverse=True
    )

    for d in date_dirs:
        script_path = os.path.join(SCRIPT_ROOT, d, "script.txt")
        if not os.path.exists(script_path):
            continue

        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()

        # 從逐字稿第一行當作標題（主題摘要）
        lines = script_text.splitlines()
        title = lines[0] if lines else f"每日播報：{d}"
        pub_date = datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
        audio_url = f"{B2_BASE_URL}/daily-podcast-stk-{d}.mp3"

        # 加入項目
        fe = fg.add_entry()
        fe.title(title)
        fe.pubDate(pub_date)
        fe.description(script_text)
        fe.enclosure(audio_url, 0, "audio/mpeg")  # 不需要 file size，Apple Podcast 可接受

# 儲存
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
fg.rss_file(OUTPUT_PATH)
print("✅ 已產生 podcast.xml，使用 Backblaze B2 音檔連結")