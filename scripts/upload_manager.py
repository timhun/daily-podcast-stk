import os
import argparse
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# ====== 參數設定 ======
parser = argparse.ArgumentParser()
parser.add_argument('--mode', default='us', choices=['tw','us'], help='播客模式')
args = parser.parse_args()
mode = args.mode.lower()

# 台灣時區日期
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today = now.strftime("%Y%m%d")
folder = f"{today}_{mode}"
identifier = f"daily-podcast-stk-{folder}"
print("🪪 上傳 identifier：", identifier)

# ====== 環境變數 ======
key_id = os.environ["B2_KEY_ID"]
application_key = os.environ["B2_APPLICATION_KEY"]
bucket_name = os.environ["B2_BUCKET_NAME"]

# ====== 連接 B2 ======
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", key_id, application_key)
bucket = b2_api.get_bucket_by_name(bucket_name)

# ====== 確認檔案 ======
base_path = f"docs/podcast/{folder}"
audio_path = os.path.join(base_path, "audio.mp3")
script_path = os.path.join(base_path, "script.txt")

if not os.path.exists(audio_path):
    print(f"⚠️ 找不到 audio.mp3：{audio_path}")
if not os.path.exists(script_path):
    print(f"⚠️ 找不到 script.txt：{script_path}")

# ====== 上傳檔案 ======
if os.path.exists(audio_path):
    bucket.upload_local_file(
        local_file=audio_path,
        file_name=f"{identifier}.mp3",
        content_type="audio/mpeg"
    )
if os.path.exists(script_path):
    bucket.upload_local_file(
        local_file=script_path,
        file_name=f"{identifier}.txt",
        content_type="text/plain"
    )

# ====== 產生 archive_audio_url.txt ======
audio_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com/{identifier}.mp3"
script_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com/{identifier}.txt"

with open(os.path.join(base_path, "archive_audio_url.txt"), "w") as f:
    f.write(f"{audio_url}\n{script_url}")

print("✅ B2 上傳完成：", audio_url)
print("✅ script 連結：", script_url)