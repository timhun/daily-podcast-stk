import os
import xml.etree.ElementTree as ET

rss_dir = "docs/rss"
us_feed_path = os.path.join(rss_dir, "podcast_us.xml")
tw_feed_path = os.path.join(rss_dir, "podcast_tw.xml")
merged_feed_path = os.path.join(rss_dir, "podcast.xml")

# ✅ 檢查檔案是否存在
feeds = []
if os.path.exists(us_feed_path):
    print("✅ 發現 podcast_us.xml")
    feeds.append(ET.parse(us_feed_path))
else:
    print("⚠️ 找不到 podcast_us.xml")

if os.path.exists(tw_feed_path):
    print("✅ 發現 podcast_tw.xml")
    feeds.append(ET.parse(tw_feed_path))
else:
    print("⚠️ 找不到 podcast_tw.xml")

if not feeds:
    raise FileNotFoundError("❌ 無任何可用 RSS feed 來源，無法合併")

# ✅ 取第一個為主架構
base_tree = feeds[0]
base_root = base_tree.getroot()
base_channel = base_root.find("channel")

# 移除現有項目
for item in base_channel.findall("item"):
    base_channel.remove(item)

# 加入每個來源的 items
all_items = []
for tree in feeds:
    root = tree.getroot()
    channel = root.find("channel")
    items = channel.findall("item")
    all_items.extend(items)

# 依 pubDate 排序（新 → 舊）
def get_pubdate(item):
    pub_date = item.find("pubDate")
    return pub_date.text if pub_date is not None else ""

all_items.sort(key=get_pubdate, reverse=True)

# 只保留同一天最新的 us 與 tw 各一集
latest = {}
for item in all_items:
    title = item.findtext("title", default="")
    if "_us" in title.lower():
        key = "us"
    elif "_tw" in title.lower():
        key = "tw"
    else:
        continue
    if key not in latest:
        latest[key] = item

# 寫入合併結果
for item in latest.values():
    base_channel.append(item)

ET.indent(base_tree, space="  ", level=0)
base_tree.write(merged_feed_path, encoding="utf-8", xml_declaration=True)
print(f"✅ 已合併 RSS feed，輸出至：{merged_feed_path}")