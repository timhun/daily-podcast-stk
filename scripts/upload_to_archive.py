import os
import re
import datetime
import requests

# 載入 AWS-S3 格式的 archive.org 憑證（可從 https://archive.org/account/s3.php 取得）
ACCESS_KEY = os.getenv("ARCHIVE_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("ARCHIVE_SECRET_ACCESS_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    raise ValueError("請設定環境變數 ARCHIVE_ACCESS_KEY_ID 和 ARCHIVE_SECRET_ACCESS_KEY")

# 今天的日期與資料夾
today = datetime.datetime.utcnow().strftime("%Y%m%d")
local_dir = f"podcast/{today}"
docs_dir = f"docs/podcast/{today}"

# DNS-safe identifier（符合 archive.org 要求）
def to_dns_safe(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\-]', '', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

identifier = to_dns_safe(f"daily-podcast-stk-{today}")
print("🪪 上傳的 identifier 為：", identifier)

# 檔案路徑
audio_path = os.path.join(local_dir, "audio.mp3")
script_path = os.path.join(local_dir, "script.txt")
cover_path = "img/cover.jpg"

if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到 audio.mp3")
if not os.path.exists(script_path):
    raise FileNotFoundError("找不到逐字稿 script.txt")
if not os.path.exists(cover_path):
    raise FileNotFoundError("找不到封面圖 img/cover.jpg")

# 準備檔案與 metadata
files = {
    f"{identifier}.mp3": open(audio_path, "rb"),
    f"{identifier}_script.txt": open(script_path, "rb"),
    f"{identifier}_cover.jpg": open(cover_path, "rb"),
}

metadata = {
    "title": f"幫幫忙說財經科技投資 - {today}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙",
    "description": "每日更新的財經科技 AI 投資播報節目，由幫幫忙主持",
    "language": "zh",
    "subject": "Podcast, Finance, AI, Investment, Tech, Daily"
}

print("🔼 正在上傳至 archive.org...")

# 發送 POST 請求到 archive S3 API
r = requests.post(
    f"https://s3.us.archive.org/{identifier}",
    auth=(ACCESS_KEY, SECRET_KEY),
    files=files,
    data=metadata
)

# 結果處理
if r.status_code == 200:
    print("✅ 上傳成功！")
    archive_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"

    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "archive_audio_url.txt"), "w") as f:
        f.write(archive_url)

    print("📄 mp3 archive URL 已儲存至 archive_audio_url.txt")
else:
    print("❌ 上傳失敗：", r.status_code)
    print(r.text)
    raise Exception("上傳 archive.org 失敗")
