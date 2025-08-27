from feedgen.feed import FeedGenerator
from slack_sdk import WebClient
import os
import datetime
import pytz  # Add pytz for timezone support

def generate_rss(date, mode, script, audio_url):
    fg = FeedGenerator()
    fg.title('幫幫忙說財經科技投資')
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

    rss_path = 'rss/combined.xml'
    fg.rss_file(rss_path, pretty=True)
    print(f"RSS updated: {rss_path}")

def notify_slack(date, mode, audio_url):
    client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
    message = f"New {mode.upper()} podcast episode for {date} is ready! Audio: {audio_url}\nRSS: https://f005.backblazeb2.com/file/{os.getenv('B2_BUCKET_NAME')}/rss/combined.xml (host RSS yourself)"
    client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
