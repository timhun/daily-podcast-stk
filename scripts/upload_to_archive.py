import os
import datetime
import requests
import re

# ✅ 檢查環境變數
ARCHIVE_EMAIL = os.getenv("ARCHIVE_EMAIL")
ARCHIVE_PASSWORD = os.getenv("ARCHIVE_PASSWORD")
if not ARCHIVE_EMAIL or not ARCHIVE_PASSWORD:
    raise ValueError("請設定 ARCHIVE_EMAIL 與 ARCHIVE_PASSWORD 環境變數")

# ✅ 今日日期與資料夾
today = datetime.datetime.utcnow().strftime("%Y%m%d")
folder = f"docs/podcast/{today}"
script_path = os.path.join(folder, "script.txt")
audio_path = os.path.join(folder, "audio.mp3")
cover_path = "img/cover.jpg"  # 使用專案內共用封面

# ✅ 檢查檔案存在
if not os.path.exists(script_path):
    raise FileNotFoundError("❌ 找不到逐字稿 script.txt")
if not os.path.exists(audio_path):
    raise FileNotFoundError("❌ 找不到音檔 audio.mp3")
if not os.path.exists(cover_path):
    raise FileNotFoundError("❌ 找不到封面 img/cover.jpg")

# ✅ 載入逐字稿內容當作說明
with open(script_path, encoding="utf-8") as f:
    description = f.read().strip()

# ✅ 建立合法 DNS-safe identifier
def to_dns_safe(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\-]', '', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

identifier_base = "daily-podcast-stk"
identifier = to_dns_safe(f"{identifier_base}-{today}")
print("🪪 上傳的 identifier 為：", identifier)

# ✅ Metadata
metadata = {
    "title": f"幫幫忙說財經科技投資 - {today}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙",
    "language": "zh",
    "description": description,
    "subject": "Podcast, Finance, AI, Investment, Tech, Daily"
}

# ✅ 準備檔案
files = {
    f"{identifier}.mp3": open(audio_path, "rb"),
    f"{identifier}.txt": open(script_path, "rb"),
    f"{identifier}.jpg": open(cover_path, "rb")
}

# ✅ 上傳
print("🔼 正在上傳至 archive.org...")
res = requests.post(
    f"https://s3.us.archive.org/{identifier}",
    auth=(ARCHIVE_EMAIL, ARCHIVE_PASSWORD),
    files=files,
    data=metadata
)

# ✅ 結果判斷
if res.status_code == 200:
    print("✅ 上傳成功！")
else:
    print("❌ 上傳失敗：", res.status_code)
    print(res.text)
    raise Exception("上傳 archive.org 失敗")

# ✅ 儲存音訊連結供 generate_rss.py 使用
archive_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
with open(f"{folder}/archive_audio_url.txt", "w") as f:
    f.write(archive_url)

print("📄 已儲存 archive_audio_url.txt")
