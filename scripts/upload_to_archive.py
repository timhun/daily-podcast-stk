import requests
import os
import datetime

ARCHIVE_EMAIL = os.environ["ARCHIVE_EMAIL"]
ARCHIVE_PASSWORD = os.environ["ARCHIVE_PASSWORD"]

AUDIO_PATH = "podcast/latest/audio.mp3"

# identifier = 範例：daily-podcast-stk-20250717
import re
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier_base = "daily-podcast-stk"
identifier = re.sub(r'[^a-z0-9\-]', '', f"{identifier_base}-{today_str}".lower())
print("🪪 上傳的 identifier 為：", identifier)

# 建立 metadata
metadata = {
    "title": f"Daily Podcast - {today_str}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙說財經科技投資",
    "description": "每天更新的財經科技AI投資語音播報節目",
    "language": "zh",
    "subject": "Podcast, Finance, AI, Investment, Tech, Daily"
}

# 上傳
files = {
    f"{identifier}.mp3": open(AUDIO_PATH, "rb")
}

print("🔼 正在上傳 mp3 至 archive.org...")

r = requests.post(
    f"https://s3.us.archive.org/{identifier}",
    auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
    files=files,
    data=metadata
)

if r.status_code == 200:
    print("✅ 上傳成功！")
else:
    print("❌ 上傳失敗：", r.status_code, r.text)
    raise Exception("上傳 archive.org 失敗")

# 輸出 URL 給 generate_rss 用
mp3_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
with open("archive_audio_url.txt", "w") as f:
    f.write(mp3_url)

print("✅ 輸出 mp3 URL 完成")
