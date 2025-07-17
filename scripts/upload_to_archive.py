import requests
import os
import datetime
import re

# 讀取帳號資訊
ARCHIVE_EMAIL = os.environ["ARCHIVE_EMAIL"]
ARCHIVE_PASSWORD = os.environ["ARCHIVE_PASSWORD"]

# 檔案路徑
AUDIO_PATH = "podcast/latest/audio.mp3"
COVER_PATH = "img/cover.jpg"

# 日期與合法 identifier
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier = re.sub(r'[^a-z0-9\-]', '', f"daily-podcast-stk-{today_str}".lower())

print("🪪 上傳的 identifier 為：", identifier)

# 上傳 mp3（使用 PUT）
with open(AUDIO_PATH, "rb") as f:
    print("📤 上傳 mp3 中...")
    r = requests.put(
        f"https://s3.us.archive.org/{identifier}/{identifier}.mp3",
        auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
        data=f
    )
    if r.status_code == 200:
        print("✅ mp3 上傳成功")
    else:
        print("❌ mp3 上傳失敗：", r.status_code, r.text)
        raise Exception("mp3 上傳失敗")

# 上傳封面（可選）
if os.path.exists(COVER_PATH):
    with open(COVER_PATH, "rb") as f:
        print("🖼️ 上傳封面 cover.jpg 中...")
        r = requests.put(
            f"https://s3.us.archive.org/{identifier}/cover.jpg",
            auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
            data=f
        )
        if r.status_code == 200:
            print("✅ 封面上傳成功")
        else:
            print("⚠️ 封面上傳失敗：", r.status_code, r.text)

# 設定 metadata（使用 POST /metadata）
metadata = {
    "title": f"幫幫忙說財經科技投資 - {today_str}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙說財經科技投資",
    "description": "每天更新的財經、科技、AI、投資語音播報節目",
    "language": "zh",
    "subject": "Podcast, 財經, AI, 投資, 科技, 中文, 每日"
}

print("📝 設定 metadata 中...")

r = requests.post(
    f"https://archive.org/metadata/{identifier}",
    auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
    data=metadata
)

if r.status_code == 200:
    print("✅ metadata 設定成功")
else:
    print("⚠️ metadata 設定失敗：", r.status_code, r.text)

# 儲存 mp3 下載網址供 RSS 使用
mp3_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
with open("archive_audio_url.txt", "w") as f:
    f.write(mp3_url)

print("🎯 輸出 mp3 URL 完成：", mp3_url)
