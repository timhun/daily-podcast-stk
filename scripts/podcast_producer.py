#podcast_producer.py
import os
import logging
import subprocess
from datetime import datetime
import pytz

logging.basicConfig(filename='logs/podcast_producer.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def main(mode_input=None):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
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
    
    if not os.path.exists(script_file):
        logging.error(f"Missing script for {mode}")
        return
    
    # Use edge-tts via subprocess (assume installed)
    cmd = [
        "edge-tts",
        "--voice", config['voice'],
        "--text", open(script_file, 'r', encoding='utf-8').read(),
        "--write-media", audio_file
    ]
    try:
        subprocess.run(cmd, check=True)
        file_size = os.path.getsize(audio_file)
        logging.info(f"Generated audio: {audio_file}, size: {file_size} bytes")
    except Exception as e:
        logging.error(f"TTS error: {e}")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    main(mode)
