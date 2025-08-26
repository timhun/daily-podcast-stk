import argparse
import datetime
import os
from dotenv import load_dotenv
from data_collector import collect_data
from content_creator import generate_script
from voice_producer import generate_audio
from cloud_manager import upload_episode
from podcast_distributor import generate_rss, notify_slack

load_dotenv()

def main(mode):
    today = datetime.date.today().strftime('%Y%m%d')
    print(f"Starting {mode.upper()} podcast production for {today}...")

    # 步驟1: 收集數據
    market_data = collect_data(mode)

    # 步驟2: 生成文字稿 (包含簡單分析)
    script = generate_script(market_data, mode)
    script_path = f"episodes/{today}_{mode}/script.txt"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    # 步驟3: 生成音頻
    audio_path = f"episodes/{today}_{mode}/audio.mp3"
    generate_audio(script_path, audio_path)

    # 步驟4: 上傳到 B2
    files = {'script': script_path, 'audio': audio_path}
    uploaded_urls = upload_episode(today, mode, files)
    audio_url = uploaded_urls['audio']

    # 步驟5: 生成 RSS + Slack 通知
    generate_rss(today, mode, script, audio_url)
    notify_slack(today, mode, audio_url)

    print("Podcast production completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=['us', 'tw'])
    args = parser.parse_args()
    main(args.mode)
