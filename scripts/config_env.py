import os

# === Backblaze B2 ===
B2_KEY_ID = os.environ.get("B2_KEY_ID")
APPLICATION_KEY = os.environ.get("B2_APPLICATION_KEY")
BUCKET_NAME = os.environ.get("B2_BUCKET_NAME")

# B2 上傳 URL 樣板
def get_audio_url(identifier: str) -> str:
    return f"https://{BUCKET_NAME}.s3.us-east-005.backblazeb2.com/{identifier}.mp3"

# === Slack ===
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")

# === Email ===
EMAIL = "Tim.oneway@gmail.com"

# === Podcast RSS ===
SITE_URL = "https://timhun.github.io/daily-podcast-stk"
B2_BASE = "https://f005.backblazeb2.com/file/daily-podcast-stk"
COVER_URL = f"{SITE_URL}/img/cover.jpg"

# === RSS 路徑設定（支持環境變數覆蓋） ===
RSS_US_PATH = os.getenv("RSS_US_PATH", "docs/rss/podcast_us.xml")
RSS_TW_PATH = os.getenv("RSS_TW_PATH", "docs/rss/podcast_tw.xml")
RSS_OUTPUT_PATH = os.getenv("RSS_OUTPUT_PATH", "docs/rss/podcast.xml")

# 根據模式決定要寫哪個 RSS 檔案
PODCAST_MODE = os.getenv("PODCAST_MODE", "tw").lower()
RSS_FILE = f"docs/rss/podcast_{PODCAST_MODE}.xml"