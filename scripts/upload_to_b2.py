import os
import datetime
from b2sdk.v2 import InMemoryAccountInfo, B2Api
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 使用台灣時區取得日期
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today = now.strftime("%Y%m%d")

# 取得 podcast 模式（預設 tw）
PODCAST_MODE = os.getenv("PODCAST_MODE", "tw").lower()
folder = f"{today}_{PODCAST_MODE}"
identifier = f"daily-podcast-stk-{folder}"
logger.info(f"🪪 上傳 identifier：{identifier}")

# 讀取環境變數
try:
    key_id = os.environ["B2_KEY_ID"]
    application_key = os.environ["B2_APPLICATION_KEY"]
    bucket_name = os.environ["B2_BUCKET_NAME"]
except KeyError as e:
    logger.error(f"⚠️ 缺少環境變數: {e}")
    raise EnvironmentError(f"⚠️ 缺少環境變數: {e}")

# 連接 B2
try:
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", key_id, application_key)
    bucket = b2_api.get_bucket_by_name(bucket_name)
    logger.info(f"✅ 已連接至 B2 儲存桶: {bucket_name}")
except Exception as e:
    logger.error(f"⚠️ B2 連接失敗: {e}")
    raise ConnectionError(f"⚠️ B2 連接失敗: {e}")

# 確認檔案存在
base_path = f"docs/podcast/{folder}"
audio_path = os.path.join(base_path, "audio.mp3")
script_path = os.path.join(base_path, "script.txt")

if not os.path.exists(audio_path):
    logger.error(f"⚠️ 找不到 audio.mp3：{audio_path}")
    raise FileNotFoundError(f"⚠️ 找不到 audio.mp3：{audio_path}")
if not os.path.exists(script_path):
    logger.error(f"⚠️ 找不到 script.txt：{script_path}")
    raise FileNotFoundError(f"⚠️ 找不到 script.txt：{script_path}")

# 上傳至 B2
try:
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
    logger.info(f"✅ 已上傳 {identifier}.mp3 和 {identifier}.txt 至 B2")
except Exception as e:
    logger.error(f"⚠️ B2 上傳失敗: {e}")
    raise RuntimeError(f"⚠️ B2 上傳失敗: {e}")

# 產出下載連結並儲存
try:
    audio_url = f"https://{bucket_name}.s3.us-east-005.backblazeb2.com/{identifier}.mp3"
    os.makedirs(base_path, exist_ok=True)
    with open(os.path.join(base_path, "archive_audio_url.txt"), "w", encoding="utf-8") as f:
        f.write(audio_url)
    logger.info(f"✅ B2 上傳完成：{audio_url}")
except Exception as e:
    logger.error(f"⚠️ 儲存下載連結失敗: {e}")
    raise IOError(f"⚠️ 儲存下載連結失敗: {e}")
