import os
import sys
import logging
from datetime import datetime, timedelta
from feedgen.feed import FeedGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# B2 公開網址基底 (換成你自己的 bucket domain)
B2_BASE_URL = "https://f002.backblazeb2.com/file/your-bucket-name"

def get_today_folder(mode: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"docs/podcast/{today}_{mode}"

def ensure_archive_url_file(folder: str) -> str:
    """
    確保 archive_audio_url.txt 存在，如果沒有就用 mp3 自動生成
    """
    url_file = os.path.join(folder, "archive_audio_url.txt")
    if os.path.exists(url_file):
        return url_file

    # 找 mp3
    mp3_files = [f for f in os.listdir(folder) if f.endswith(".mp3")]
    if not mp3_files:
        raise FileNotFoundError(f"❌ 沒找到 MP3 檔案：{folder}")

    latest_mp3 = sorted(mp3_files)[-1]
    mp3_url = f"{B2_BASE_URL}/{latest_mp3}"

    # 自動寫入
    with open(url_file, "w", encoding="utf-8") as f:
        f.write(mp3_url + "\n")

    logger.warning(f"⚠️ 找不到 archive_audio_url.txt，自動生成 {url_file}")
    return url_file

def generate_rss(mode: str):
    folder = get_today_folder(mode)
    os.makedirs(folder, exist_ok=True)

    archive_url_file = ensure_archive_url_file(folder)

    with open(archive_url_file, "r", encoding="utf-8") as f:
        audio_urls = [line.strip() for line in f if line.strip()]

    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title("每日投資 Podcast")
    fg.link(href="https://yourdomain.com/rss.xml", rel="self")
    fg.description("每日自動生成的投資廣播")
    fg.language("zh-TW")

    for url in audio_urls:
        fe = fg.add_entry()
        fe.id(url)
        fe.title(f"每日播客 {datetime.now().strftime('%Y-%m-%d')} ({mode.upper()})")
        fe.enclosure(url, 0, "audio/mpeg")

    rss_file = f"docs/rss/{mode}_feed.xml"
    os.makedirs("docs/rss", exist_ok=True)
    fg.rss_file(rss_file)
    logger.info(f"✅ RSS 生成完成：{rss_file}")

if __name__ == "__main__":
    mode = os.environ.get("PODCAST_MODE") or (sys.argv[sys.argv.index("--mode")+1] if "--mode" in sys.argv else "tw")
    generate_rss(mode)