import os
import logging
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from datetime import datetime, timedelta
import pytz

logging.basicConfig(filename='logs/upload_manager.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def cleanup_old_files(b2_api, bucket, days=14):
    now = datetime.now(pytz.utc)
    for version in bucket.ls(recursive=True):
        file_info = version[0]
        upload_time = datetime.fromtimestamp(file_info.upload_timestamp / 1000, tz=pytz.utc)
        if (now - upload_time) > timedelta(days=days):
            b2_api.delete_file_version(file_info.id_, file_info.file_name)
            logging.info(f"Deleted old file: {file_info.file_name}")

def main(mode_input=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", os.environ['B2_KEY_ID'], os.environ['B2_APPLICATION_KEY'])
    bucket = b2_api.get_bucket_by_name(os.environ['B2_BUCKET_NAME'])
    
    tw_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tw_tz)
    today_str = now.strftime('%Y%m%d')
    
    if mode_input:
        mode = mode_input
    else:
        mode = 'us' if now.hour < 12 else 'tw'
    
    dir_path = f"docs/podcast/{today_str}_{mode}"
    script_file = f"{dir_path}/script.txt"
    audio_file = f"{dir_path}/audio.mp3"
    url_file = f"{dir_path}/archive_audio_url.txt"
    
    if not os.path.exists(audio_file) or not os.path.exists(script_file):
        logging.error(f"Missing files for {mode}")
        return
    
    # Upload audio
    remote_audio = f"{today_str}_{mode}/audio.mp3"
    bucket.upload_local_file(local_file=audio_file, file_name=remote_audio)
    audio_url = f"{config['b2_base_url']}/{remote_audio}"
    
    # Upload script
    remote_script = f"{today_str}_{mode}/script.txt"
    bucket.upload_local_file(local_file=script_file, file_name=remote_script)
    script_url = f"{config['b2_base_url']}/{remote_script}"
    
    with open(url_file, 'w') as f:
        f.write(audio_url + '\n' + script_url)
    logging.info(f"Uploaded: {audio_url}, {script_url}")
    
    # Cleanup
    cleanup_old_files(b2_api, bucket)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    main(mode)
