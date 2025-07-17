import requests
import os
import datetime
import re

# 讀取環境變數
ARCHIVE_EMAIL = os.environ["ARCHIVE_EMAIL"]
ARCHIVE_PASSWORD = os.environ["ARCHIVE_PASSWORD"]

# 檔案路徑
AUDIO_PATH = "podcast/latest/audio.mp3"
COVER_PATH = "img/cover.jpg"  # ← 你的封面圖路徑

# 產生合法的 identifier
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier_base = "daily-podcast-stk"
identifier = re.sub(r'[^a-z0-9\-]', '', f"{identifier_base}-{today_str}".lower())

print("🪪 上傳的 identifier 為：", identifier)

# 檔名
mp3_name = f"{identifier}.mp3"

# 建立 metadata
metadata = {
    "title": f"幫幫忙說財經科技投資 - {today_str}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙說財經科技投資",
    "description": "每天更新的財經、科技、AI、投資語音播報節目",
    "language": "zh",
    "subject": "Podcast, 財經, AI, 投資, 科技, 中文, 每日"
}

# 🔼 上傳 mp3 + 封面圖（確保縮排正確）
print("🔼 正在上傳 mp3 與封面至 archive.org...")

with open(AUDIO_PATH, "rb") as audio_file, open(COVER_PATH, "rb") as cover_file:
    files = {
        mp3_name: audio_file,
        "cover.jpg": cover_file
    }

    r = requests.post(
        f"https://s3.us.archive.org/{identifier}",
        auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
        files=files,
        data=metadata,
        headers={
            "Host": "s3.us.archive.org"  # ← 修正 Virtual Host 錯誤
        }
    )

    if r.status_code == 200:
        print("✅ 上傳成功！")
    else:
        print("❌ 上傳失敗：", r.status_code, r.text)
        raise Exception("上傳 archive.org 失敗")

# 📝 輸出 mp3 URL 給 generate_rss.py 使用
mp3_url = f"https://archive.org/download/{identifier}/{mp3_name}"
with open("archive_audio_url.txt", "w") as f:
    f.write(mp3_url)

print("✅ 輸出 mp3 URL 完成：", mp3_url)
