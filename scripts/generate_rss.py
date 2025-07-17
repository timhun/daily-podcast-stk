import os
import requests
from feedgen.feed import FeedGenerator
from datetime import datetime

# 從 upload_to_archive.py 輸出的檔案中讀取 archive.org mp3 連結
with open("archive_audio_url.txt", "r") as f:
    audio_url = f.read().strip()

# 使用 HEAD 請求取得音檔大小（byte）
res = requests.head(audio_url)
file_size = int(res.headers.get("Content-Length", 0))

# 建立 RSS feed
fg = FeedGenerator()
fg.load_extension('podcast')

fg.title("幫幫忙說財經科技投資")  # 節目名稱
fg.link(href="https://timhun.github.io/daily-podcast-stk/rss/podcast.xml", rel="self")
fg.description("每天早上更新的財經、科技、AI、投資語音節目")  # 節目簡介
fg.language("zh-TW")

# 新增一集內容
fe = fg.add_entry()
today = datetime.today().strftime("%Y/%m/%d")
fe.title(f"每日播報：{today}")
fe.pubDate(datetime.now())
fe.description("今天的財經科技投資重點播報")
fe.enclosure(audio_url, file_size, "audio/mpeg")

# 輸出 RSS 到指定位置（GitHub Pages 中的 rss 資料夾）
fg.rss_file("docs/rss/podcast.xml")
