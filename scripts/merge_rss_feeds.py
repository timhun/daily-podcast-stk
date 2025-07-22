import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# 載入兩個 feed
tree_us = ET.parse("docs/podcast_us.xml")
tree_tw = ET.parse("docs/podcast_tw.xml")

root_us = tree_us.getroot()
root_tw = tree_tw.getroot()

channel_us = root_us.find("channel")
channel_tw = root_tw.find("channel")

# 建立新 RSS root
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

# 複製 channel_us 中除了 <item> 的內容
for child in channel_us:
    if child.tag != "item":
        channel.append(child)

# 合併所有 items
items = channel_us.findall("item") + channel_tw.findall("item")

# 依照 pubDate 過濾出 us / tw 各一集最新
latest = {}
for item in items:
    title = item.find("title").text or ""
    pub_date = item.find("pubDate").text
    dt = parsedate_to_datetime(pub_date)
    mode = "us" if "us" in title.lower() else "tw"
    if mode not in latest or dt > latest[mode][0]:
        latest[mode] = (dt, item)

# 加入最新的 us / tw 兩個 item
for _, item in sorted(latest.values(), key=lambda x: x[0], reverse=True):
    channel.append(item)

# 輸出 RSS
tree = ET.ElementTree(rss)
tree.write("docs/podcast.xml", encoding="utf-8", xml_declaration=True)
