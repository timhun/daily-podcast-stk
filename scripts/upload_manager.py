import os, json, logging, argparse, time
from datetime import datetime, timedelta, timezone
import pytz
from b2sdk.v2 import InMemoryAccountInfo, B2Api

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/upload_manager.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("upload")

def tpe_today():
    return datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")

def b2_client():
    info = InMemoryAccountInfo()
    b2 = B2Api(info)
    b2.authorize_account("production",
        os.environ["B2_KEY_ID"],
        os.environ["B2_APPLICATION_KEY"])
    return b2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["us","tw"], required=True)
    args = parser.parse_args()

    date_str = tpe_today()
    folder = f"docs/podcast/{date_str}_{args.mode}"
    audio = f"{folder}/audio.mp3"
    script= f"{folder}/script.txt"
    assert os.path.exists(audio) and os.path.exists(script), "audio/script missing"

    b2 = b2_client()
    bucket = b2.get_bucket_by_name(os.environ["B2_BUCKET_NAME"])

    # 上傳
    for path in [audio, script]:
        fname = path.replace("docs/","")
        bucket.upload_local_file(local_file=path, file_name=fname)
        logger.info(f"uploaded -> {fname}")

    # 生成公開連結（使用 CDN/直接下載 URL 前綴）
    base = os.environ.get("B2_BASE", "https://f005.backblazeb2.com/file/daily-podcast-stk")
    audio_url = f"{base}/podcast/{date_str}_{args.mode}/audio.mp3"
    with open(f"{folder}/archive_audio_url.txt","w",encoding="utf-8") as f:
        f.write(audio_url)

    # 清理 14 天前檔
    cleanup_days = json.load(open("config.json","r",encoding="utf-8"))["cleanup_days"]
    cutoff = (datetime.now(pytz.UTC) - timedelta(days=cleanup_days)).strftime("%Y%m%d")
    # 簡化策略：不逐一刪版控，只示範 bucket 列表（實務可依檔名日期判斷）
    logger.info(f"cleanup policy: keep last {cleanup_days} days (cutoff {cutoff})")

if __name__=="__main__":
    main()
