import os
from datetime import datetime, timezone
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# 讀取環境變數
key_id = os.environ["B2_KEY_ID"]
app_key = os.environ["B2_KEY"]
bucket_id = os.environ["B2_BUCKET_NAME"]  # 注意：此為 bucket "ID"（若使用限制 bucket 金鑰）

# 日期字串
today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
print("🪪 上傳的 identifier 為：", today_str)

# 路徑
folder = f"docs/podcast/{today_str}"
audio_path = f"{folder}/audio.mp3"
script_path = f"{folder}/script.txt"

# 檢查檔案是否存在
if not os.path.exists(audio_path):
    raise FileNotFoundError("❌ 找不到 audio.mp3")
if not os.path.exists(script_path):
    raise FileNotFoundError("❌ 找不到 script.txt")

# 初始化 B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, app_key)
bucket = b2_api.get_bucket_by_id(bucket_id)

# 上傳 mp3
audio_file_name = f"podcast/{today_str}/audio.mp3"
print(f"🎵 上傳 mp3: {audio_file_name}")
with open(audio_path, "rb") as f:
    bucket.upload_bytes(f.read(), audio_file_name, content_type="audio/mpeg")

# 上傳逐字稿
script_file_name = f"podcast/{today_str}/script.txt"
print(f"📜 上傳 script.txt: {script_file_name}")
with open(script_path, "rb") as f:
    bucket.upload_bytes(f.read(), script_file_name, content_type="text/plain")

# 公開下載網址（適用於 public bucket）
download_url = f"https://f000.backblazeb2.com/file/{bucket.name}/podcast/{today_str}/audio.mp3"
with open("archive_audio_url.txt", "w") as f:
    f.write(download_url)

print("✅ 已成功上傳至 Backblaze B2")
print("🔗 下載連結：", download_url)