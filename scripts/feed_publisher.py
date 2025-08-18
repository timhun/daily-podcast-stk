import os
import json
from datetime import datetime
import logging
import requests
from mutagen.easyid3 import EasyID3
from argparse import ArgumentParser

# 設定日誌
logging.basicConfig(filename='logs/feed_publisher.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(mode=None):
    """載入 config.json 配置文件"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        platforms = config.get('platforms', {
            'spotify': {'enabled': True},
            'apple': {'enabled': True},
            'google': {'enabled': False, 'api_key': ''}
        })
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL', config.get('slack_webhook_url', ''))
        return platforms, slack_webhook
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def load_inputs(mode):
    """載入分析結果和音頻檔案資訊"""
    date_str = datetime.now().strftime("%Y%m%d")
    analysis_path = os.path.join('data', f'market_analysis_0050.TW.json' if mode == 'tw' else f'market_analysis_QQQ.json')
    audio_path = os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'audio.mp3')
    url_path = os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'archive_audio_url.txt')

    if not os.path.exists(analysis_path) or not os.path.exists(audio_path) or not os.path.exists(url_path):
        logger.error(f"缺少輸入文件: {analysis_path}, {audio_path}, 或 {url_path}")
        return None, None, None

    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        with open(url_path, 'r', encoding='utf-8') as f:
            download_url = f.read().strip()
        audio = EasyID3(audio_path) if os.path.exists(audio_path) else {'length': '0'}
        logger.info(f"載入輸入: 分析 {analysis.get('recommendation', 'N/A')}, URL {download_url}, 音頻長度 {audio.get('length', '0')}")
        return analysis, download_url, audio
    except Exception as e:
        logger.error(f"載入輸入失敗: {e}")
        return None, None, None

def generate_rss_xml(analysis, download_url, mode):
    """生成 RSS XML 內容"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"{datetime.now().strftime('%H:%M')} {'台股' if mode == 'tw' else '美股'} 市場播客"
    description = f"市場建議: {analysis.get('recommendation', 'N/A')}\n風險評估: {analysis.get('risk_note', '無')}"
    duration = analysis.get('duration', '0:00')  # 假設從音頻元數據獲取

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{title}</title>
    <link>https://example.com/podcast</link>
    <description>每日市場分析播客</description>
    <pubDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
    <item>
      <title>{title}</title>
      <description>{description}</description>
      <pubDate>{date_str}</pubDate>
      <enclosure url="{download_url}" length="1024" type="audio/mpeg"/>
      <itunes:duration>{duration}</itunes:duration>
      <guid>{download_url}</guid>
    </item>
  </channel>
</rss>"""
    logger.info(f"生成 RSS XML: 長度 {len(rss)} 字元")
    return rss

def push_to_platforms(rss, platforms):
    """推播至 Spotify/Apple Podcast（模擬）"""
    success = []
    for platform, config in platforms.items():
        if config.get('enabled', False):
            # 這裡模擬推播，實際需使用 API（如 Spotify Web API 或 Apple Podcast Connect）
            logger.info(f"模擬推播至 {platform}: 成功")
            success.append(platform)
    return success

def send_slack_notification(analysis, download_url, platforms):
    """發送 Slack 通知"""
    slack_webhook = platforms.get('slack_webhook', '')
    if not slack_webhook:
        logger.warning("缺少 Slack Webhook URL，跳過通知")
        return

    message = {
        "text": f"播客更新 - {datetime.now().strftime('%Y-%m-%d %H:%M')}:\n"
                f"建議: {analysis.get('recommendation', 'N/A')}\n"
                f"下載連結: {download_url}\n"
                f"推播平台: {', '.join(platforms)}"
    }
    try:
        response = requests.post(slack_webhook, json=message, timeout=10)
        response.raise_for_status()
        logger.info(f"Slack 通知成功: {response.text}")
    except Exception as e:
        logger.error(f"Slack 通知失敗: {e}")

def save_rss(rss, mode):
    """保存 RSS XML 檔案"""
    output_dir = os.path.join('docs', 'rss')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'podcast_{mode}.xml')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rss)
        logger.info(f"RSS 保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存 RSS 失敗: {e}")

def main(mode='tw'):
    """主函數，執行推播發佈"""
    platforms, slack_webhook = load_config(mode)
    analysis, download_url, audio = load_inputs(mode)
    if analysis and download_url and audio:
        rss = generate_rss_xml(analysis, download_url, mode)
        save_rss(rss, mode)
        pushed_platforms = push_to_platforms(rss, platforms)
        send_slack_notification(analysis, download_url, pushed_platforms)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='推播員腳本')
    parser.add_argument('--mode', default='tw', choices=['tw', 'us'], help='播客模式 (tw/us)')
    args = parser.parse_args()
    main(args.mode)