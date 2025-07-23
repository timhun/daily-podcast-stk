import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import os

# 📁 路徑設定
rss_us_path = "docs/rss/podcast_us.xml"
rss_tw_path = "docs/rss/podcast_tw.xml"
output_path = "docs/rss/podcast.xml"

# ✅ 檢查來源檔案
if not os.path.exists(rss_us_path) or not os.path.exists(rss_tw_path):
    print("❌ 缺少 podcast_us.xml 或 podcast_tw.xml")
    exit(1)

print("✅ 發現 podcast_us.xml")
print("✅ 發現 podcast_tw.xml")

# ✅ 解析原始 RSS
tree_us = ET.parse(rss_us_path)
tree_tw = ET.parse(rss_tw_path)
root_us = tree_us.getroot()
root_tw = tree_tw.getroot()
channel_us = root_us.find("channel")
channel_tw = root_tw.find("channel")

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

# ✅ 複製 channel metadata（不含 item）
for elem in list(channel_us):
    if elem.tag != "item":
        channel.append(elem)

# ✅ 收集兩個來源的所有 item
items = channel_us.findall("item") + channel_tw.findall("item")

# ✅ 根據 pubDate 挑出 us / tw 各一集最新的集數
latest = {}

for item in items:
    title_elem = item.find("title")
    pub_elem = item.find("pubDate")
    if title_elem is None or pub_elem is None:
        continue

    title = title_elem.text or ""
    pub_date = pub_elem.text

    try:
        dt = parsedate_to_datetime(pub_date)
    except Exception:
        print(f"⚠️ 無法解析 pubDate：{title}")
        continue

    # 判斷集數是 us 還是 tw
    if "_us" in title.lower():
        mode = "us"
    elif "_tw" in title.lower():
        mode = "tw"
    else:
        print(f"⚠️ 無法判斷集數是 us 或 tw：{title}")
        continue

    print(f"✅ 發現 {mode} 集數：{title}")

    # 若尚未收錄或是更晚的 pubDate，則取代
    if mode not in latest or dt > latest[mode][0]:
        latest[mode] = (dt, item)

# ✅ 寫入最新的 us / tw 集數（依時間順序）
for _, item in sorted(latest.values(), key=lambda x: x[0], reverse=True):
    channel.append(item)

# ✅ 輸出合併後的 RSS
tree = ET.ElementTree(rss)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
tree.write(output_path, encoding="utf-8", xml_declaration=True)
print(f"✅ 已合併 RSS feed，輸出至：{output_path}")
