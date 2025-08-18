import os
import json
from datetime import datetime, timedelta
import logging
import zipfile
from b2sdk.v1 import InMemoryAccountInfo, B2Api
from argparse import ArgumentParser

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
        b2_config = config.get('b2', {
            'key_id': os.getenv('B2_KEY_ID', ''),
            'application_key': os.getenv('B2_APPLICATION_KEY', ''),
            'bucket_name': os.getenv('B2_BUCKET_NAME', 'podcast-bucket')
        })
        s3_config = config.get('s3', {'enabled': False})  # 未來擴充
        return b2_config, s3_config
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def create_zip_archive(mode):
    """壓縮 MP3 和文字稿檔案"""
    date_str = datetime.now().strftime("%Y%m%d")
    input_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    if not os.path.exists(input_dir):
        logger.error(f"缺少輸入目錄: {input_dir}")
        raise FileNotFoundError(f"缺少輸入目錄: {input_dir}")

    zip_path = os.path.join(input_dir, f'podcast_{date_str}_{mode}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in ['audio.mp3', 'script.txt']:
            file_path = os.path.join(input_dir, file)
            if os.path.exists(file_path):
                zipf.write(file_path, file)
                logger.info(f"壓縮 {file} 至 {zip_path}")
    zip_size = os.path.getsize(zip_path) / 1024  # 單位: KB
    logger.info(f"壓縮檔案生成: {zip_path}, 大小 {zip_size:.2f} KB")
    return zip_path

def upload_to_b2(zip_path, b2_config):
    """上傳至 Backblaze B2 並生成下載連結"""
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", b2_config['key_id'], b2_config['application_key'])
    bucket = b2_api.get_bucket_by_name(b2_config['bucket_name'])

    file_name = os.path.basename(zip_path)
    upload_file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
    file_info = bucket.upload_local_file(
        local_file=zip_path,
        file_name=upload_file_name
    )
    download_url = f"https://{b2_config['bucket_name']}.s3.us-west-000.backblazeb2.com/{upload_file_name}"
    logger.info(f"上傳成功: {upload_file_name}, 下載連結: {download_url}")
    return download_url

def clean_old_files():
    """刪除 14 天前的檔案"""
    now = datetime.now()
    podcast_dir = os.path.join('docs', 'podcast')
    if not os.path.exists(podcast_dir):
        logger.warning(f"目錄不存在: {podcast_dir}")
        return

    deleted_files = []
    for root, _, files in os.walk(podcast_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_date_str = os.path.basename(root).split('_')[0]  # 從目錄名提取日期
            try:
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                if (now - file_date).days > 14:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"刪除舊檔案: {file_path}")
            except ValueError:
                logger.warning(f"無法解析日期: {file_date_str}, 跳過 {file_path}")
    if deleted_files:
        logger.info(f"總共清理 {len(deleted_files)} 個檔案: {', '.join(deleted_files)}")
    else:
        logger.info("無需清理舊檔案")

def save_download_link(download_url, mode):
    """保存下載連結"""
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'archive_audio_url.txt')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(download_url)
        logger.info(f"下載連結保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存下載連結失敗: {e}")

def main(mode='tw'):
    """主函數，執行上傳管理"""
    b2_config, s3_config = load_config(mode)
    if not b2_config['key_id'] or not b2_config['application_key'] or not b2_config['bucket_name']:
        logger.error("缺少 B2 認證資訊")
        raise ValueError("缺少 B2 認證資訊")

    zip_path = create_zip_archive(mode)
    download_url = upload_to_b2(zip_path, b2_config)
    save_download_link(download_url, mode)
    clean_old_files()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='雲端上傳員腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    args = parser.parse_args()
    main(args.mode)