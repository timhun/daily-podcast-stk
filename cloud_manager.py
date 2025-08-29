from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os
import json

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def upload_episode(date, mode, files):
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", os.getenv('B2_KEY_ID'), os.getenv('B2_APPLICATION_KEY'))
    bucket = b2_api.get_bucket_by_name(os.getenv('B2_BUCKET_NAME'))

    uploaded = {}
    for file_type, file_path in files.items():
        # 使用根目錄，檔案名稱保持 daily-podcast-stk-YYYYMMDD_{mode}.{ext}
        file_name = os.path.basename(file_path)  # 提取 daily-podcast-stk-YYYYMMDD_{mode}.mp3 或 .txt
        bucket.upload_local_file(local_file=file_path, file_name=file_name)
        uploaded[file_type] = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{file_name}"
    return uploaded

def upload_rss(rss_path):
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", os.getenv('B2_KEY_ID'), os.getenv('B2_APPLICATION_KEY'))
    bucket = b2_api.get_bucket_by_name(os.getenv('B2_BUCKET_NAME'))

    # 上傳 RSS 到 B2 儲存桶根目錄，命名為 podcast.xml
    b2_file_name = "podcast.xml"
    bucket.upload_local_file(local_file=rss_path, file_name=b2_file_name)
    rss_url = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{b2_file_name}"
    return rss_url
