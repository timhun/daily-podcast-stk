import os
import datetime
import requests
import re

# ✅ 讀取環境變數（使用 Access Key 認證）
ACCESS_KEY = os.getenv("ARCHIVE_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("ARCHIVE_SECRET_ACCESS_KEY")
if not ACCESS_KEY or not SECRET_KEY:
    raise ValueError("❌ 請設定 ARCHIVE_ACCESS_KEY_ID 與 ARCHIVE_SECRET_ACCESS_KEY")

# ✅ 今日日期
today = datetime.datetime.utcnow().strftime("%Y%m%d")
folder = f"docs/podcast/{today}"
script_path = os.path.join(folder, "script.txt")
audio_path = os.path.join(folder, "audio.mp3")
cover_path = "img/cover.jpg"

# ✅ 檢查檔案存在
if not os.path.exists(audio_path):
    raise FileNotFoundError(f"❌ 找不到音檔 {audio_path}")
if not os.path.exists(script_path):
    raise FileNotFoundError(f"❌ 找不到逐字稿 {script_path}")
if not os.path.exists(cover_path):
    raise FileNotFoundError(f"❌ 找不到封面 {cover_path}")

# ✅ 載入逐字稿內容當作 description
with open(script_path, encoding="utf-8") as f:
    description = f.read().strip()

# ✅ 建立 DNS-safe 的 identifier（符合 archive.org 要求）
def to_dns_safe(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\-]', '', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

identifier = to_dns_safe(f"daily-podcast-stk-{today}")
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

# ✅ 上傳至 archive.org 的 S3 接口
print("🔼 正在上傳至 archive.org...")

response = requests.post(
    f"https://s3.us.archive.org/{identifier}",
    auth=(ACCESS_KEY, SECRET_KEY),
    files=files,
    data=metadata
)

# ✅ 檢查回應
if response.status_code == 200:
    print("✅ 上傳成功！")
else:
    print("❌ 上傳失敗：", response.status_code)
    print(response.text)
    raise Exception("上傳 archive.org 失敗")

# ✅ 儲存 mp3 archive 下載網址，供 RSS 用
archive_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
output_path = os.path.join(folder, "archive_audio_url.txt")
with open(output_path, "w") as f:
    f.write(archive_url)

print("📄 已儲存：", output_path)
