#merge_rss_feeds.py
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import os
import logging
from datetime import datetime

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 📁 路徑設定（支持環境變數覆蓋）
rss_us_path = os.getenv('RSS_US_PATH', 'docs/rss/podcast_us.xml')
rss_tw_path = os.getenv('RSS_TW_PATH', 'docs/rss/podcast_tw.xml')
output_path = os.getenv('RSS_OUTPUT_PATH', 'docs/rss/podcast.xml')

# ✅ 檢查來源檔案
if not os.path.exists(rss_us_path):
    logger.error(f"❌ 缺少 podcast_us.xml: {rss_us_path}")
    exit(1)
if not os.path.exists(rss_tw_path):
    logger.error(f"❌ 缺少 podcast_tw.xml: {rss_tw_path}")
    exit(1)

logger.info(f"✅ 發現 podcast_us.xml: {rss_us_path}")
logger.info(f"✅ 發現 podcast_tw.xml: {rss_tw_path}")

# ✅ 解析原始 RSS
try:
    tree_us = ET.parse(rss_us_path)
    tree_tw = ET.parse(rss_tw_path)
    root_us = tree_us.getroot()
    root_tw = tree_tw.getroot()
    channel_us = root_us.find("channel")
    channel_tw = root_tw.find("channel")
    if channel_us is None or channel_tw is None:
        logger.error("❌ 無法找到 channel 節點")
        exit(1)
except ET.ParseError as e:
    logger.error(f"❌ XML 解析錯誤: {e}")
    exit(1)

# ✅ 建立新的 RSS 根節點（保留完整命名空間）
rss = ET.Element(
    "rss",
    {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:atom": "http://www.w3.org/2005/Atom",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
    }
)
channel = ET.SubElement(rss, "channel")

# ✅ 複製 channel metadata（不含 item）從 US 版本
for elem in list(channel_us):
    if elem.tag != "item":
        channel.append(elem)

# ✅ 添加合併時間戳
last_build_date = ET.SubElement(channel, "lastBuildDate")
last_build_date.text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

# ✅ 收集兩個來源的所有 item
items = channel_us.findall("item") + channel_tw.findall("item")

# ✅ 根據 pubDate 挑出 us / tw 各一集最新的集數
latest = {}

for item in items:
    title_elem = item.find("title")
    pub_elem = item.find("pubDate")
    if title_elem is None or pub_elem is None:
        logger.warning("⚠️ 項目缺少 title 或 pubDate，跳過")
        continue

    title = title_elem.text or ""
    pub_date = pub_elem.text

    try:
        dt = parsedate_to_datetime(pub_date)
    except Exception as e:
        logger.warning(f"⚠️ 無法解析 pubDate 為 {title}: {e}")
        continue

    # 判斷集數是 us 還是 tw
    if "_us" in title.lower():
        mode = "us"
    elif "_tw" in title.lower():
        mode = "tw"
    else:
        logger.warning(f"⚠️ 無法判斷集數是 us 或 tw: {title}")
        continue

    logger.info(f"✅ 發現 {mode} 集數: {title}")

    # 若尚未收錄或是更晚的 pubDate，則取代
    if mode not in latest or dt > latest[mode][0]:
        latest[mode] = (dt, item)

# ✅ 寫入最新的 us / tw 集數（依時間順序）
for _, item in sorted(latest.values(), key=lambda x: x[0], reverse=True):
    channel.append(item)

# ✅ 輸出合併後的 RSS
try:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree = ET.ElementTree(rss)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info(f"✅ 已合併 RSS feed，輸出至: {output_path}")
except Exception as e:
    logger.error(f"❌ 寫入 RSS 檔案失敗: {e}")
    exit(1)
