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

    folder = f"{config['data_paths']['podcast']}/{date}_{mode}/"
    uploaded = {}
    for file_type, file_path in files.items():
        file_name = folder + os.path.basename(file_path)
        bucket.upload_local_file(local_file=file_path, file_name=file_name)
        uploaded[file_type] = f"https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/{file_name}"
    return uploaded
