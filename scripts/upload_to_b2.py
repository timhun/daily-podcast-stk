import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# 讀取環境變數
application_key_id = os.environ["B2_KEY_ID"]
application_key = os.environ["B2_KEY"]
bucket_name = os.environ["B2_BUCKET_NAME"]

# 日期
today = datetime.datetime.utcnow().strftime("%Y%m%d")
local_audio_path = f"docs/podcast/{today}/audio.mp3"
local_script_path = f"docs/podcast/{today}/script.txt"
remote_audio_filename = f"{today}.mp3"
remote_script_filename = f"{today}.txt"

# 初始化 B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", application_key_id, application_key)

# 取得 Bucket（此方法需 key 有權限）
bucket = b2_api.get_bucket_by_name(bucket_name)

# 上傳 audio.mp3
if not os.path.exists(local_audio_path):
    raise FileNotFoundError("❌ 找不到音檔 audio.mp3")

with open(local_audio_path, "rb") as f:
    bucket.upload_bytes(f.read(), remote_audio_filename)
    print("✅ audio.mp3 上傳成功")

# 上傳 script.txt
if os.path.exists(local_script_path):
    with open(local_script_path, "rb") as f:
        bucket.upload_bytes(f.read(), remote_script_filename)
        print("✅ script.txt 上傳成功")
else:
    print("⚠️ 找不到 script.txt，略過上傳")

# 儲存連結供 RSS 使用
b2_url = f"https://f000.backblazeb2.com/file/{bucket_name}/{remote_audio_filename}"
with open("b2_audio_url.txt", "w") as f:
    f.write(b2_url)
print("✅ B2 連結已儲存：", b2_url)