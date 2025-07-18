import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# 設定日期
today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today_str}"
print("🪪 上傳的 identifier 為：", identifier)

# 讀取環境變數
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ.get("B2_APPLICATION_KEY") 
bucket_name = os.environ["B2_BUCKET_NAME"]

# 初始化 B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)
bucket = b2_api.get_bucket_by_name(bucket_name)

# 檢查檔案
audio_path = f"docs/podcast/{today_str}/audio.mp3"
script_path = f"docs/podcast/{today_str}/script.txt"

if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到 audio.mp3")

if not os.path.exists(script_path):
    raise FileNotFoundError("找不到 script.txt")

# 上傳 audio.mp3
audio_dest_name = f"{identifier}.mp3"
print("🔼 正在上傳 audio.mp3 至 B2...")
bucket.upload_local_file(
    local_file=audio_path,
    file_name=audio_dest_name,
    content_type="audio/mpeg"
)

# 上傳 script.txt
script_dest_name = f"{identifier}.txt"
print("🔼 正在上傳 script.txt 至 B2...")
bucket.upload_local_file(
    local_file=script_path,
    file_name=script_dest_name,
    content_type="text/plain"
)

# 產出音訊 URL 給 generate_rss.py 用
base_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com"
audio_url = f"{base_url}/{audio_dest_name}"
with open("archive_audio_url.txt", "w") as f:
    f.write(audio_url)

print("✅ 上傳 B2 完成，音訊連結：", audio_url)
