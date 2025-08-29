from feedgen.feed import FeedGenerator
from slack_sdk import WebClient
import os
import datetime
import pytz
import json

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def generate_rss(date, mode, script, audio_url):
    fg = FeedGenerator()
    fg.title('幫幫忙說AI投資')
    fg.description('AI驅動的每日財經投資分析')
    fg.author({'name': '幫幫忙', 'email': os.getenv('EMAIL')})
    fg.language('zh-tw')
    fg.link(href=audio_url, rel='alternate')

    fe = fg.add_entry()
    fe.title(f"{mode.upper()} 版 - {datetime.date.today()}")
    fe.description(script[:200] + '...')  # 簡短描述
    fe.enclosure(audio_url, 0, 'audio/mpeg')
    # Use timezone-aware datetime (UTC)
    fe.pubDate(datetime.datetime.now(pytz.UTC))

    rss_path = config['data_paths']['rss']
    os.makedirs(os.path.dirname(rss_path), exist_ok=True)  # Create 'docs/rss' directory if it doesn't exist
    fg.rss_file(rss_path, pretty=True)
    print(f"RSS updated: {rss_path}")

def notify_slack(date, mode, audio_url):
    client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
    message = f"New {mode.upper()} podcast episode for {date} is ready! Audio: {audio_url}"
    client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
    print(f"Slack notification sent for {mode} episode on {date}")
