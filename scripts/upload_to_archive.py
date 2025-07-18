import os
import re
import datetime
import boto3
from botocore.client import Config

# 載入憑證（從 GitHub Secrets 或 local 設定）
ACCESS_KEY = os.getenv("ARCHIVE_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("ARCHIVE_SECRET_ACCESS_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    raise ValueError("請設定環境變數 ARCHIVE_ACCESS_KEY_ID 與 ARCHIVE_SECRET_ACCESS_KEY")

# 產生 DNS-safe identifier
today = datetime.datetime.utcnow().strftime("%Y%m%d")

def to_dns_safe(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9\-]', '', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

identifier = to_dns_safe(f"daily-podcast-stk-{today}")
print("🪪 上傳的 identifier 為：", identifier)

# 檔案路徑
local_dir = f"docs/podcast/{today}"
audio_path = os.path.join(local_dir, "audio.mp3")
script_path = os.path.join(local_dir, "script.txt")
cover_path = "img/cover.jpg"

if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到 audio.mp3")
if not os.path.exists(script_path):
    raise FileNotFoundError("找不到逐字稿 script.txt")
if not os.path.exists(cover_path):
    raise FileNotFoundError("找不到封面圖 img/cover.jpg")

# 建立 boto3 client（IA endpoint）
s3 = boto3.client(
    "s3",
    endpoint_url="https://s3.us.archive.org",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version='s3')
)

# 上傳檔案
def upload_file(local_path, key):
    print(f"📤 上傳 {key} 中...")
    s3.upload_file(local_path, identifier, key)

upload_file(audio_path, f"{identifier}.mp3")
upload_file(script_path, f"{identifier}_script.txt")
upload_file(cover_path, f"{identifier}_cover.jpg")

# 上傳 metadata
print("📝 上傳 metadata.xml...")
metadata_txt = f"""
<metadata>
  <title>幫幫忙說財經科技投資 - {today}</title>
  <mediatype>audio</mediatype>
  <collection>opensource_audio</collection>
  <creator>幫幫忙</creator>
  <language>zh</language>
  <description>每日更新的財經科技 AI 投資語音節目</description>
  <subject>Podcast, Finance, AI, Investment, Tech</subject>
</metadata>
""".strip()

s3.put_object(
    Bucket=identifier,
    Key="metadata.xml",
    Body=metadata_txt.encode("utf-8")
)

# 儲存 mp3 URL
archive_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
with open(os.path.join(local_dir, "archive_audio_url.txt"), "w") as f:
    f.write(archive_url)

print("✅ 全部上傳完成！")
print("🔗 音檔網址：", archive_url)
