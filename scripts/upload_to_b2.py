import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# ✅ 使用台灣時區取得日期
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today = now.strftime("%Y%m%d")

PODCAST_MODE = os.getenv("PODCAST_MODE", "us").lower()
folder = f"{today}_{PODCAST_MODE}"
identifier = f"daily-podcast-stk-{folder}"
print("🪪 上傳 identifier：", identifier)

# ✅ 讀取環境變數
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ["B2_APPLICATION_KEY"]
bucket_name = os.environ["B2_BUCKET_NAME"]

# ✅ 連接 B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)
bucket = b2_api.get_bucket_by_name(bucket_name)

# ✅ 確認檔案存在
base_path = f"docs/podcast/{folder}"
audio_path = os.path.join(base_path, "audio.mp3")
script_path = os.path.join(base_path, "script.txt")

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"⚠️ 找不到 audio.mp3：{audio_path}")
if not os.path.exists(script_path):
    raise FileNotFoundError(f"⚠️ 找不到 script.txt：{script_path}")

# ✅ 上傳至 B2
bucket.upload_local_file(
    local_file=audio_path,
    file_name=f"{identifier}.mp3",
    content_type="audio/mpeg"
)
bucket.upload_local_file(
    local_file=script_path,
    file_name=f"{identifier}.txt",
    content_type="text/plain"
)

# ✅ 產出下載連結並儲存
audio_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com/{identifier}.mp3"
with open(os.path.join(base_path, "archive_audio_url.txt"), "w") as f:
    f.write(audio_url)

print("✅ B2 上傳完成：", audio_url)