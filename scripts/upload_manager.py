import os
import json
from datetime import datetime, timedelta
import logging
import zipfile
from b2sdk.v1 import InMemoryAccountInfo, B2Api
from b2sdk.v1 import B2UploadStreamFailed
import argparse

# 設定日誌
logging.basicConfig(filename='logs/upload_manager.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(mode=None):
    """載入 config.json 配置文件"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        b2_config = {
            'key_id': os.getenv('B2_KEY_ID'),
            'application_key': os.getenv('B2_APPLICATION_KEY'),
            'bucket_name': config.get('b2_bucket_name', 'your-b2-bucket-name')
        }
        s3_config = config.get('s3', {'enabled': False, 'access_key': '', 'secret_key': '', 'bucket_name': ''})
        return b2_config, s3_config, config.get('retain_days', 14)
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def compress_files(input_dir, output_zip):
    """壓縮 MP3 和文字稿檔案"""
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(input_dir):
                file_path = os.path.join(input_dir, file)
                if file in ['audio.mp3', 'script.txt']:
                    zipf.write(file_path, os.path.basename(file_path))
        size_kb = os.path.getsize(output_zip) / 1024
        logger.info(f"壓縮完成: {output_zip}, 大小 {size_kb:.2f} KB")
        return output_zip
    except Exception as e:
        logger.error(f"壓縮失敗: {e}")
        return None

def upload_to_b2(b2_config, zip_path, mode, date_str):
    """上傳至 Backblaze B2"""
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", b2_config['key_id'], b2_config['application_key'])
        bucket = b2_api.get_bucket_by_name(b2_config['bucket_name'])
        file_name = f"podcast/{date_str}_{mode}/archive.zip"
        with open(zip_path, 'rb') as f:
            file_info = bucket.upload(f, file_name)
        download_url = f"https://{b2_config['bucket_name']}.s3.us-west-000.backblazeb2.com/{file_name}"
        logger.info(f"B2 上傳成功: {file_name}, 下載連結: {download_url}")
        return download_url
    except B2UploadStreamFailed as e:
        logger.error(f"B2 上傳失敗: {e}")
        return None
    except Exception as e:
        logger.error(f"B2 上傳過程中發生錯誤: {e}")
        return None

def upload_to_s3(s3_config, zip_path, mode, date_str):
    """上傳至 AWS S3（未實現，需安裝 boto3）"""
    if not s3_config['enabled']:
        logger.warning("S3 未啟用，跳過