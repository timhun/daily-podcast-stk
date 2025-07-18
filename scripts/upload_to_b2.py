import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api, UploadSourceBytes

# 讀取環境變數
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ["B2_APPLICATION_KEY"]
bucket_name = os.environ["B2_BUCKET_NAME"]

# 取得今天日期
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
folder = f"docs/podcast/{today_str}"
filename_audio = "audio.mp3"
filename_script = "script.txt"

# 檢查檔案存在
audio_path = os.path.join(folder, filename_audio)
script_path = os.path.join(folder, filename_script)

if not os.path.exists(audio_path):
    raise FileNotFoundError("找不到 audio.mp3")

if not os.path.exists(script_path):
    raise FileNotFoundError("找不到 script.txt")

# 初始化 B2
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)
bucket = b2_api.get_bucket_by_name(bucket_name)

# 上傳 audio.mp3
with open(audio_path, "rb") as f:
    bucket.upload_bytes(f.read(), f"podcast/{today_str}/{filename_audio}")
    print("✅ audio.mp3 上傳成功")

# 上傳 script.txt
with open(script_path, "rb") as f:
    bucket.upload_bytes(f.read(), f"podcast/{today_str}/{filename_script}")
    print("✅ script.txt 上傳成功")

# 輸出公開音訊連結（給 RSS 用）
public_url = f"https://f000.backblazeb2.com/file/{bucket_name}/podcast/{today_str}/{filename_audio}"
with open(os.path.join(folder, "b2_audio_url.txt"), "w") as f:
    f.write(public_url)

print("📤 上傳完成，音訊網址：", public_url)
