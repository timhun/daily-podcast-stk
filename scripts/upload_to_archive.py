import os
import datetime
import mimetypes
import boto3
from botocore.client import Config

# 讀取憑證
access_key = os.getenv("ARCHIVE_ACCESS_KEY_ID")
secret_key = os.getenv("ARCHIVE_SECRET_ACCESS_KEY")

if not access_key or not secret_key:
    raise ValueError("請設定環境變數 ARCHIVE_ACCESS_KEY_ID 與 ARCHIVE_SECRET_ACCESS_KEY")

# 取得今天日期
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today_str}"
print("🪪 上傳的 identifier 為：", identifier)

# 檔案來源路徑
base_dir = f"docs/podcast/{today_str}"
audio_path = os.path.join(base_dir, "audio.mp3")
script_path = os.path.join(base_dir, "script.txt")
cover_path = "img/cover.jpg"  # 可選

if not os.path.exists(audio_path):
    raise FileNotFoundError("❌ 找不到 audio.mp3")

if not os.path.exists(script_path):
    raise FileNotFoundError("❌ 找不到 script.txt")

# 準備 S3 client
s3 = boto3.client(
    "s3",
    endpoint_url="https://s3.us.archive.org",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3")
)

# 建立 metadata（第一次上傳需要）
metadata = {
    "title": f"幫幫忙說財經科技投資 {today_str}",
    "mediatype": "audio",
    "collection": "opensource_audio",
    "creator": "幫幫忙",
    "language": "zh",
    "description": "每日財經科技投資播報 Podcast 節目",
    "subject": "Podcast, Finance, AI, Investment, Tech, Daily"
}

# ⬆ 上傳檔案函式
def upload_file(file_path, object_name):
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    print(f"📤 上傳 {object_name} 中...")
    with open(file_path, "rb") as f:
        s3.upload_fileobj(
            f,
            identifier,
            object_name,
            ExtraArgs={"ContentType": mime_type}
        )

# 上傳 metadata.xml（建立項目）
s3.put_object(Bucket=identifier, Key="_meta.xml", Body="\n".join(f"<{k}>{v}</{k}>" for k, v in metadata.items()), ContentType="text/xml")

# 上傳音檔與腳本
upload_file(audio_path, f"{identifier}.mp3")
upload_file(script_path, f"{identifier}_script.txt")

# 可選上傳封面（img/cover.jpg）
if os.path.exists(cover_path):
    upload_file(cover_path, f"{identifier}_cover.jpg")

# 產出 archive 下載連結
archive_url = f"https://archive.org/download/{identifier}/{identifier}.mp3"
with open(os.path.join(base_dir, "archive_audio_url.txt"), "w") as f:
    f.write(archive_url)

print("✅ 上傳成功！")
print("🎧 音檔網址：", archive_url)
