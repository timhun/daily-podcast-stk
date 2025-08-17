import os
import json
from datetime import datetime, timedelta
import logging
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置檔案和環境變數
CONFIG_FILE = 'config.json'

def load_config():
    """載入配置檔案 config.json"""
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"缺少配置檔案: {CONFIG_FILE}")
        raise FileNotFoundError(f"缺少配置檔案: {CONFIG_FILE}")
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', [])
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def connect_to_b2():
    """連接至 Backblaze B2"""
    try:
        key_id = os.environ["B2_KEY_ID"]
        application_key = os.environ["B2_APPLICATION_KEY"]
        bucket_name = os.environ["B2_BUCKET_NAME"]
    except KeyError as e:
        logger.error(f"⚠️ 缺少環境變數: {e}")
        raise EnvironmentError(f"⚠️ 缺少環境變數: {e}")

    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, application_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        logger.info(f"✅ 已連接至 B2 儲存桶: {bucket_name}")
        return bucket
    except Exception as e:
        logger.error(f"⚠️ B2 連接失敗: {e}")
        raise ConnectionError(f"⚠️ B2 連接失敗: {e}")

def upload_file(bucket, local_path, identifier, content_type):
    """上傳單一檔案到 B2"""
    try:
        file_name = f"{identifier}.{os.path.splitext(local_path)[1][1:]}"
        bucket.upload_local_file(
            local_file=local_path,
            file_name=file_name,
            content_type=content_type
        )
        logger.info(f"✅ 已上傳 {file_name} 至 B2")
        return file_name
    except Exception as e:
        logger.error(f"⚠️ 上傳 {local_path} 失敗: {e}")
        raise RuntimeError(f"⚠️ 上傳失敗: {e}")

def generate_download_url(bucket_name, file_name):
    """生成 B2 下載連結"""
    return f"https://{bucket_name}.s3.us-east-005.backblazeb2.com/{file_name}"

def save_upload_url(output_dir, url):
    """保存 B2 上傳後的公開連結"""
    url_path = os.path.join(output_dir, 'archive_audio_url.txt')
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(url_path, 'w', encoding='utf-8') as f:
            f.write(url)
        logger.info(f"✅ 下載連結保存至 {url_path}")
    except Exception as e:
        logger.error(f"⚠️ 儲存下載連結失敗: {e}")
        raise IOError(f"⚠️ 儲存下載連結失敗: {e}")

def cleanup_old_files(base_dir='docs/podcast', retain_days=14):
    """刪除 14 天前的檔案"""
    now = datetime.now()
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_date_str = os.path.basename(root).split('_')[0]  # 假設目錄名如 20250817_tw
            try:
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                if (now - file_date).days > retain_days:
                    os.remove(file_path)
                    logger.info(f"✅ 刪除過期檔案: {file_path}")
            except ValueError:
                logger.warning(f"無法解析日期格式: {file_date_str}, 跳過 {file_path}")

def main():
    """主函數，執行雲端上傳"""
    current_hour = datetime.now().hour
    if current_hour not in [6, 14]:  # 僅 6am 和 2pm 上傳
        logger.info(f"當前時間 {current_hour}:00 CST 不在上傳時段，跳過")
        return

    mode = 'us' if current_hour == 6 else 'tw'
    date_str = datetime.now().strftime("%Y%m%d")
    podcast_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    identifier = f"daily-podcast-stk-{date_str}_{mode}"

    # 連接 B2
    bucket = connect_to_b2()

    # 確認並上傳檔案
    files_to_upload = [
        {'path': os.path.join(podcast_dir, 'audio.mp3'), 'type': 'audio/mpeg'},
        {'path': os.path.join(podcast_dir, 'script.txt'), 'type': 'text/plain'}
    ]

    for file_info in files_to_upload:
        file_path = file_info['path']
        if os.path.exists(file_path):
            uploaded_file_name = upload_file(bucket, file_path, identifier, file_info['type'])
            if uploaded_file_name:
                url = generate_download_url(bucket.name, uploaded_file_name)
                save_upload_url(podcast_dir, url)
        else:
            logger.warning(f"⚠️ 檔案不存在，跳過上傳: {file_path}")

    # 清理舊檔案
    cleanup_old_files()

if __name__ == '__main__':
    main()
