import os
import xml.etree.ElementTree as ET

rss_files = [
    "docs/rss/podcast_us.xml",
    "docs/rss/podcast_tw.xml"
]

output_file = "docs/rss/podcast.xml"

def parse_rss_items(path):
    if not os.path.exists(path):
        return None, []
    tree = ET.parse(path)
    root = tree.getroot()
    channel = root.find("channel")
    items = channel.findall("item") if channel else []
    return channel, items

# 複製第一個的 channel 結構
main_channel, _ = parse_rss_items(rss_files[0])
if main_channel is None:
    print("❌ 找不到主 RSS 結構")
    exit(1)

# 清空原有 item
for item in main_channel.findall("item"):
    main_channel.remove(item)

# 加入每個來源的一集
for path in rss_files:
    _, items = parse_rss_items(path)
    if items:
        main_channel.append(items[0])

# 輸出合併後 RSS
tree = ET.ElementTree(main_channel.getparent())
tree.write(output_file, encoding="utf-8", xml_declaration=True)
print(f"✅ 合併完成：{output_file}")
