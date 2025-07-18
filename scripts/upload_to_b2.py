import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# 從環境變數讀取 Backblaze 認證
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ["B2_KEY"]
bucket_name = os.environ["B2_BUCKET_NAME"]

# 今日日期（用於檔名）
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
identifier = f"daily-podcast-stk-{today_str}"
print("🪪 上傳的 identifier 為：", identifier)

# 建立 B2 API 實例
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)

# 取得指定 bucket
bucket = b2_api.get_bucket_by_name(bucket_name)

# 要上傳的檔案路徑
local_dir = f"docs/podcast/{today_str}"
audio_path = f"{local_dir}/audio.mp3"
script_path = f"{local_dir}/script.txt"

if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到 audio.mp3")

if not os.path.exists(script_path):
    raise FileNotFoundError("找不到逐字稿 script.txt")

# 上傳音檔
print("🎧 上傳 audio.mp3 中...")
bucket.upload_local_file(
    local_file=audio_path,
    file_name=f"{identifier}/audio.mp3",
    content_type="audio/mpeg"
)

# 上傳逐字稿
print("📜 上傳 script.txt 中...")
bucket.upload_local_file(
    local_file=script_path,
    file_name=f"{identifier}/script.txt",
    content_type="text/plain"
)

# 儲存 mp3 連結供 RSS 使用
b2_url = f"https://f000.backblazeb2.com/file/{bucket_name}/{identifier}/audio.mp3"
with open("b2_audio_url.txt", "w") as f:
    f.write(b2_url)

print("✅ 上傳完成並產生 b2_audio_url.txt")