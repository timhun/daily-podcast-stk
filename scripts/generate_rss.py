import os
from feedgen.feed import FeedGenerator
from datetime import datetime

# 設定音檔位置與 GitHub Pages 上的網址
audio_path = "podcast/latest/audio.mp3"
audio_url = "https://timhun.github.io/daily-podcast-stk/podcast/latest/audio.mp3"

# 取得檔案大小（用於 RSS enclosure）
file_size = os.path.getsize(audio_path)

# 建立 RSS feed
fg = FeedGenerator()
fg.load_extension('podcast')

fg.title("幫幫忙說財經科技投資")
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天早上更新的財經、科技、AI、投資語音節目")
fg.language("zh-TW")

# 新增一集
fe = fg.add_entry()
today = datetime.today().strftime("%Y/%m/%d")
fe.title(f"每日播報：{today}")
fe.pubDate(datetime.now())
fe.description("今天的財經科技投資重點播報")
fe.enclosure(audio_url, file_size, "audio/mpeg")

# 輸出 RSS 檔案到 GitHub Pages 專用的 docs 目錄
fg.rss_file("docs/rss/podcast.xml")

print("✅ RSS feed 已輸出完成")