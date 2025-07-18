import os
import datetime
import requests
import re

# 載入帳號
ARCHIVE_EMAIL = os.environ.get("ARCHIVE_EMAIL")
ARCHIVE_PASSWORD = os.environ.get("ARCHIVE_PASSWORD")

if not ARCHIVE_EMAIL or not ARCHIVE_PASSWORD:
    raise ValueError("請設定環境變數 ARCHIVE_EMAIL / ARCHIVE_PASSWORD")

# 取得今天日期與檔案路徑
today = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today}"

base_path = f"podcast/{today}"
audio_path = f"{base_path}/audio.mp3"
script_path = f"{base_path}/script.txt"
cover_path = "img/cover.jpg"

# 檢查檔案
if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到音訊檔案 audio.mp3")
if not os.path.exists(script_path):
    raise FileNotFoundError("找不到逐字稿 script.txt")
if not os.path.exists(cover_path):
    raise FileNotFoundError("找不到封面圖 img/cover.jpg")

# 組成 metadata
metadata = {
    "title": f"幫幫忙播報：{today}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "language": "zh",
    "creator": "幫幫忙",
    "description": "幫幫忙說財經科技投資：每日語音播報",
    "subject": "Podcast, 財經, 科技, AI, 投資, 幫幫忙",
}

# 準備檔案
files = {
    f"{identifier}.mp3": open(audio_path, "rb"),
    "script.txt": open(script_path, "rb"),
    "cover.jpg": open(cover_path, "rb"),
}

print(f"🪪 上傳 identifier：{identifier}")
print("🔼 正在上傳到 archive.org...")

upload_url = f"https://s3.us.archive.org/{identifier}"
r = requests.post(upload_url, auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD), files=files, data=metadata)

# 關閉檔案
for f in files.values():
    f.close()

if r.status_code == 200:
    print("✅ 上傳成功！")
    mp3_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
    with open("archive_audio_url.txt", "w") as f:
        f.write(mp3_url)
    print(f"🔗 mp3 URL: {mp3_url}")
else:
    print("❌ 上傳失敗：", r.status_code)
    print(r.text)
    raise Exception("上傳 archive.org 失敗")