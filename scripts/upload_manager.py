import os
import json
from datetime import datetime, timedelta
import logging
import subprocess

# 假設 upload_to_b2.py 存在並可用
# 這裡使用 subprocess 調用 upload_to_b2.py，需根據實際實現調整

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 B2 上傳參數
B2_COMMAND = "python upload_to_b2.py --file {file_path} --bucket my-bucket --public"
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

def upload_file(file_path, mode):
    """上傳檔案到 B2"""
    try:
        command = B2_COMMAND.format(file_path=file_path)
        subprocess.run(command, shell=True, check=True, text=True)
        logger.info(f"成功上傳 {file_path} 到 B2")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"上傳 {file_path} 失敗: {e}")
        return False

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
                    logger.info(f"刪除過期檔案: {file_path}")
            except ValueError:
                logger.warning(f"無法解析日期格式: {file_date_str}, 跳過 {file_path}")

def save_upload_url(file_path, mode):
    """保存 B2 上傳後的公開連結"""
    output_dir = os.path.join('docs', 'podcast', os.path.basename(os.path.dirname(file_path)))
    url_path = os.path.join(output_dir, 'archive_audio_url.txt')
    try:
        with open(url_path, 'w', encoding='utf-8') as f:
            f.write(f"https://my-bucket.fra1.digitaloceanspaces.com/{os.path.basename(file_path)}")  # 假設的 URL 格式
        logger.info(f"上傳連結保存至 {url_path}")
    except Exception as e:
        logger.error(f"保存上傳連結失敗: {e}")

def main():
    """主函數，執行雲端上傳"""
    current_hour = datetime.now().hour
    if current_hour not in [6, 14]:  # 僅 6am 和 2pm 上傳
        logger.info(f"當前時間 {current_hour}:00 CST 不在上傳時段，跳過")
        return

    mode = 'us' if current_hour == 6 else 'tw'
    date_str = datetime.now().strftime("%Y%m%d")
    podcast_dir = os.path.join('docs', 'podcast', f"{date_str}_{mode}")

    files_to_upload = [
        os.path.join(podcast_dir, 'audio.mp3'),
        os.path.join(podcast_dir, 'script.txt')
    ]

    for file_path in files_to_upload:
        if os.path.exists(file_path):
            if upload_file(file_path, mode):
                save_upload_url(file_path, mode)
        else:
            logger.warning(f"檔案不存在，跳過上傳: {file_path}")

    cleanup_old_files()

if __name__ == '__main__':
    main()
