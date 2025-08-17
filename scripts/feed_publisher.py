import os
import logging
from datetime import datetime
from xml.sax.saxutils import escape

# ===== Logger =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def publish(mode: str, script_path: str, audio_link: str) -> str:
    """
    發佈 RSS Feed，並更新 docs/rss 內容
    :param mode: "tw" 或 "us"
    :param script_path: 逐字稿檔案路徑
    :param audio_link: 音檔上傳後的連結
    :return: RSS 檔案路徑
    """
    rss_dir = "docs/rss"
    os.makedirs(rss_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    rss_file = os.path.join(rss_dir, f"feed_{mode}.xml")

    logger.info("========== RSS Publisher ==========")
    logger.info(f" Mode: {mode}")
    logger.info(f" Script: {script_path}")
    logger.info(f" Audio: {audio_link}")
    logger.info(f" RSS file: {rss_file}")

    # 讀逐字稿內容 (若存在)
    description = ""
    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                description = f.read().strip()
                # 避免 RSS 解析錯誤
                description = escape(description[:500])  # 最多存 500 字
        except Exception as e:
            logger.error(f"讀逐字稿失敗: {e}")
    else:
        logger.warning("逐字稿不存在，使用預設描述")
        description = "每日自動生成的 Podcast 節目"

    # RSS XML 內容
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Daily Podcast {mode.upper()}</title>
  <link>{audio_link}</link>
  <description>每日自動生成的 Podcast Feed</description>
  <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
  <item>
    <title>{date_str} {mode.upper()}</title>
    <description>{description}</description>
    <enclosure url="{audio_link}" type="audio/mpeg" />
    <guid>{date_str}-{mode}</guid>
    <pubDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
  </item>
</channel>
</rss>
"""

    try:
        with open(rss_file, "w", encoding="utf-8") as f:
            f.write(rss_content)
        logger.info(f"✅ RSS feed 已更新 -> {rss_file}")
    except Exception as e:
        logger.error(f"❌ 寫入 RSS 失敗: {e}")
        raise

    return rss_file


if __name__ == "__main__":
    # Debug 用：手動測試
    rss_path = publish(
        mode="tw",
        script_path="data/sample_script.txt",
        audio_link="https://example.com/audio/test.mp3"
    )
    print("RSS 生成:", rss_path)