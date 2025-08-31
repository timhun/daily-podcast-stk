from feedgen.feed import FeedGenerator
from slack_sdk import WebClient
import os
import datetime
import pytz
import json
import xml.etree.ElementTree as ET
from cloud_manager import upload_rss

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

FIXED_DESCRIPTION = """(測試階段)一個適合上班族在最短時間做短線交易策略的節目!
每集節目由涵蓋最新市場數據與 AI 趨勢，專注市值型ETF短線交易策略(因為你沒有無限資金可以東買買西買買，更沒有時間研究個股)！
\n\n讓你在 7 分鐘內快速掌握大盤動向，以獨家研製的短線大盤多空走向，
提供美股每日(SPY,QQQ)的交易策略(喜歡波動小的選SPY/QQQ,波動大的TQQQ/SOXL)。\n\n
提供台股每日(0050或00631L)的交易策略(喜歡波動小的選0050,波動大的00631L)。
\n\n
🔔 訂閱 Apple Podcasts 或 Spotify，掌握每日雙時段更新。掌握每日美股、台股、AI工具與新創投資機會！\n\n
📮 主持人：幫幫忙"""


def generate_rss(date, mode, script, audio_url):
    rss_path = config['data_paths']['rss']
    os.makedirs(os.path.dirname(rss_path), exist_ok=True)

    # 如果 RSS 檔案存在，讀取舊集數
    existing_entries = []
    if os.path.exists(rss_path):
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find('channel')
            for item in channel.findall('item'):
                entry = {
                    'title': item.find('title').text,
                    'description': item.find('description').text,
                    'enclosure_url': item.find('enclosure').get('url'),
                    'enclosure_length': item.find('enclosure').get('length'),
                    'enclosure_type': item.find('enclosure').get('type'),
                    'pubDate': item.find('pubDate').text
                }
                existing_entries.append(entry)
        except ET.ParseError as e:
            print(f"RSS 解析錯誤: {e}，重新創建 RSS。")

    # 初始化 FeedGenerator
    fg = FeedGenerator()
    fg.title('幫幫忙說AI投資')
    fg.description('AI驅動的每日財經投資分析')
    fg.author({'name': '幫幫忙', 'email': os.getenv('EMAIL')})
    fg.language('zh-tw')
    fg.link(href='https://f005.backblazeb2.com/file/daily-podcast-stk/', rel='alternate')

    # 保留舊集數
    for entry in existing_entries:
        fe = fg.add_entry()
        fe.title(entry['title'])
        fe.description(entry['description'])
        fe.enclosure(entry['enclosure_url'], entry['enclosure_length'], entry['enclosure_type'])
        fe.pubDate(entry['pubDate'])

    # 添加新集數
    TW_TZ = pytz.timezone("Asia/Taipei")
    today_title = datetime.datetime.now(TW_TZ).strftime("%Y-%m-%d")
    fe = fg.add_entry()
    fe.title(f"{mode.upper()} 版 - {today_title}")
    fe.description(script[:200] + '...')
    fe.enclosure(audio_url, 0, 'audio/mpeg')
    fe.pubDate(datetime.datetime.now(pytz.UTC))

    # 儲存 RSS 檔案
    fg.rss_file(rss_path, pretty=True)
    
    # 上傳 RSS 到 B2
    rss_url = upload_rss(rss_path)
    print(f"RSS 本地生成: {rss_path}")
    print(f"RSS 上傳至 B2: {rss_url}")

def notify_slack(date, mode, audio_url):
    client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
    message = f"New {mode.upper()} podcast episode for {date} is ready! Audio: {audio_url}"
    client.chat_postMessage(channel=os.getenv('SLACK_CHANNEL'), text=message)
    print(f"已發送 Slack 通知，{mode} 版 {date} 集數")
