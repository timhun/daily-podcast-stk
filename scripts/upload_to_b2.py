import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

mode = os.getenv("PODCAST_MODE", "us")
today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today_str}-{mode}"

# 認證資訊
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ.get("B2_APPLICATION_KEY") 
bucket_name = os.environ["B2_BUCKET_NAME"]

info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)
bucket = b2_api.get_bucket_by_name(bucket_name)

# 檔案位置
base_path = f"docs/podcast/{today_str}-{mode}"
audio_path = os.path.join(base_path, "audio.mp3")
script_path = os.path.join(base_path, "script.txt")

if not os.path.exists(audio_path) or not os.path.exists(script_path):
    raise FileNotFoundError("⚠️ 找不到必要檔案")

# 上傳 mp3
audio_dest_name = f"{identifier}.mp3"
print(f"🔼 上傳音檔至 B2：{audio_dest_name}")
bucket.upload_local_file(
    local_file=audio_path,
    file_name=audio_dest_name,
    content_type="audio/mpeg"
)

# 上傳逐字稿
script_dest_name = f"{identifier}.txt"
print(f"🔼 上傳逐字稿至 B2：{script_dest_name}")
bucket.upload_local_file(
    local_file=script_path,
    file_name=script_dest_name,
    content_type="text/plain"
)

# 產出 URL
base_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com"
audio_url = f"{base_url}/{audio_dest_name}"
with open(os.path.join(base_path, "archive_audio_url.txt"), "w") as f:
    f.write(audio_url)

print(f"✅ 上傳完成，音訊網址：{audio_url}")
