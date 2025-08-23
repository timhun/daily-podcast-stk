import os
import logging
from datetime import datetime
import pytz
import json
from slack_sdk import WebClient
import xml.etree.ElementTree as ET

logging.basicConfig(filename='logs/feed_publisher.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def generate_rss(mode, config, today_str, audio_url, analysis):
    rss_file = f"docs/rss/podcast_{mode}.xml"
    
    # Simple RSS generation (expand as needed)
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = config[f'podcast_title_{mode}']
    ET.SubElement(channel, "description").text = "Daily stock analysis"
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"{today_str} Episode"
    ET.SubElement(item, "enclosure", url=audio_url, type="audio/mpeg")
    ET.SubElement(item, "description").text = json.dumps(analysis)[:200]  # Summary
    
    tree = ET.ElementTree(root)
    tree.write(rss_file, encoding='utf-8', xml_declaration=True)
    logging.info(f"Generated RSS: {rss_file}")
    
    # Note: Submit rss_file to Spotify/Apple manually first; auto-push needs API keys

def notify_slack(mode, audio_url, analysis):
    client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
    summary = json.dumps(analysis)[:200]
    message = f"New {mode.upper()} Podcast: {audio_url}\nSummary: {summary}"
    response = client.chat_postMessage(channel=os.environ['SLACK_CHANNEL'], text=message)
    logging.info(f"Slack response: {response['ok']}")

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
    url_file = f"{dir_path}/archive_audio_url.txt"
    focus_sym = '0050TW' if mode == 'tw' else 'QQQ'
    analysis_file = f"data/market_analysis_{focus_sym}.json"
    
    if not os.path.exists(url_file) or not os.path.exists(analysis_file):
        logging.error(f"Missing files for {mode}")
        return
    
    with open(url_file, 'r') as f:
        audio_url = f.readline().strip()
    
    with open(analysis_file, 'r') as f:
        analysis = json.load(f)
    
    generate_rss(mode, config, today_str, audio_url, analysis)
    notify_slack(mode, audio_url, analysis)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    main(mode)
