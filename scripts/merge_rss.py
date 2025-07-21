import os
from xml.etree import ElementTree as ET

# 設定路徑與檔案名稱
RSS_DIR = "docs/rss"
US_RSS = os.path.join(RSS_DIR, "podcast_us.xml")
TW_RSS = os.path.join(RSS_DIR, "podcast_tw.xml")
MERGED_RSS = os.path.join(RSS_DIR, "podcast.xml")

# 讀取 RSS 檔案
us_tree = ET.parse(US_RSS)
us_root = us_tree.getroot()
us_items = us_root.find("channel").findall("item")

tw_tree = ET.parse(TW_RSS)
tw_root = tw_tree.getroot()
tw_items = tw_root.find("channel").findall("item")

# 合併 item，僅保留每天各一集（us 與 tw 各一集）
merged_items = {}

for item in us_items + tw_items:
    pub_date = item.find("pubDate").text
    mode = "us" if "美股" in item.find("title").text else "tw"
    date_key = pub_date[:16] + mode  # 例如 "Mon, 21 Jul 2025us"
    if date_key not in merged_items:
        merged_items[date_key] = item

# 建立新的 RSS Feed 樹
merged_root = us_root
channel = merged_root.find("channel")

# 移除舊的 item
for old_item in channel.findall("item"):
    channel.remove(old_item)

# 加入合併後的 item，並依時間排序
sorted_items = sorted(merged_items.values(), key=lambda i: i.find("pubDate").text, reverse=True)
for item in sorted_items:
    channel.append(item)

# 寫入整合後的 RSS
ET.indent(merged_root)
ET.ElementTree(merged_root).write(MERGED_RSS, encoding="utf-8", xml_declaration=True)
print(f"✅ 已產生合併後的 RSS Feed：{MERGED_RSS}")
