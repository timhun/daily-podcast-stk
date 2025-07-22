import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import os

# 路徑設定
rss_us_path = "docs/rss/podcast_us.xml"
rss_tw_path = "docs/rss/podcast_tw.xml"
output_path = "docs/rss/podcast.xml"

# ✅ 檢查來源檔案
if not os.path.exists(rss_us_path) or not os.path.exists(rss_tw_path):
    print("❌ 缺少 podcast_us.xml 或 podcast_tw.xml")
    exit(1)

print("✅ 發現 podcast_us.xml")
print("✅ 發現 podcast_tw.xml")

tree_us = ET.parse(rss_us_path)
tree_tw = ET.parse(rss_tw_path)
root_us = tree_us.getroot()
root_tw = tree_tw.getroot()

channel_us = root_us.find("channel")
channel_tw = root_tw.find("channel")

# ✅ 建立新的 RSS root，手動指定命名空間
rss = ET.Element(
    "rss",
    {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:atom": "http://www.w3.org/2005/Atom"
    }
)
channel = ET.SubElement(rss, "channel")

# ✅ 複製 US 的 channel metadata（非 item）
for child in channel_us:
    if child.tag != "item":
        channel.append(child)

# ✅ 收集 item
items = channel_us.findall("item") + channel_tw.findall("item")

# ✅ 分類 item，依 pubDate 留下 us / tw 各一集最新
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
        print(f"⚠️ 跳過無法解析時間的集數：{title}")
        continue

    if "_us" in title.lower():
        mode = "us"
    elif "_tw" in title.lower():
        mode = "tw"
    else:
        print(f"⚠️ 無法判斷模式（us/tw）：{title}")
        continue

    print(f"✅ 發現 {mode} 節目：{title}")

    if mode not in latest or dt > latest[mode][0]:
        latest[mode] = (dt, item)

# ✅ 寫入兩集
for _, item in sorted(latest.values(), key=lambda x: x[0], reverse=True):
    channel.append(item)

# ✅ 輸出結果
tree = ET.ElementTree(rss)
os.makedirs(os.path.dirname(output_path), exist_ok=True)
tree.write(output_path, encoding="utf-8", xml_declaration=True)
print(f"✅ 已合併 RSS feed，輸出至：{output_path}")
