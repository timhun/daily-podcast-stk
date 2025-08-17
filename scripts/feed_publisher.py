import os
import json
from datetime import datetime
import logging
import requests
from xml.etree import ElementTree as ET
from mutagen.mp3 import MP3

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置參數
CONFIG_FILE = 'config.json'
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
PODCAST_TITLE = "每日市場分析"
PODCAST_DESCRIPTION = "提供台股與美股的最新市場分析與策略建議。"
FEED_URL = "https://your-domain.com/rss/podcast_{mode}.xml"
ITUNES_CATEGORY = "Business"

def load_config():
    """載入配置檔案 config.json"""
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"缺少配置檔案: {CONFIG_FILE}")
        raise FileNotFoundError(f"缺少配置檔案: {CONFIG_FILE}")
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('symbols', [])
    except json.JSONDecodeError as e:
        logger.error(f"配置檔案解析失敗: {e}")
        raise ValueError(f"配置檔案解析失敗: {e}")

def load_analysis(symbol):
    """載入市場分析結果"""
    analysis_path = os.path.join('data', f'market_analysis_{symbol}.json')
    if not os.path.exists(analysis_path):
        logger.error(f"缺少 {analysis_path}")
        return None
    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"載入 {symbol} 分析結果失敗: {e}")
        return None

def load_strategy(symbol):
    """載入策略結果"""
    strategy_path = os.path.join('data', f'strategy_best_{symbol}.json')
    if not os.path.exists(strategy_path):
        logger.error(f"缺少 {strategy_path}")
        return None
    try:
        with open(strategy_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"載入 {symbol} 策略結果失敗: {e}")
        return None

def load_upload_url(mode):
    """載入 B2 上傳後的公開連結"""
    date_str = datetime.now().strftime("%Y%m%d")
    url_path = os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'archive_audio_url.txt')
    if not os.path.exists(url_path):
        logger.error(f"缺少上傳連結: {url_path}")
        return None
    try:
        with open(url_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"載入上傳連結失敗: {e}")
        return None

def generate_rss(mode, audio_url):
    """生成 RSS XML"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    symbol = '0050.TW' if mode == 'tw' else 'QQQ'
    analysis = load_analysis(symbol)
    strategy = load_strategy(symbol)

    rss = ET.Element("rss", version="2.0", xmlns_itunes="http://www.itunes.com/dtds/podcast-1.0.dtd", xmlns_googleplay="http://www.google.com/schemas/play-podcasts/1.0")
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = PODCAST_TITLE
    ET.SubElement(channel, "link").text = FEED_URL.format(mode=mode)
    ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, "language").text = "zh-tw" if mode == 'tw' else "en-us"
    ET.SubElement(channel, "pubDate").text = pub_date
    ET.SubElement(channel, "lastBuildDate").text = pub_date
    ET.SubElement(channel, "itunes:category", attrib={"text": ITUNES_CATEGORY})
    ET.SubElement(channel, "googleplay:category", attrib={"text": ITUNES_CATEGORY})

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"{date_str} {mode.upper()} 市場分析"
    ET.SubElement(item, "link").text = audio_url
    ET.SubElement(item, "guid").text = f"{date_str}_{mode}"
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "description").text = f"建議: {analysis.get('recommendation', 'N/A')}, 倉位: {analysis.get('position_size', 0.0)}, 策略回報: {strategy.get('return', 'N/A')}%"
    audio = MP3(os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'audio.mp3'))
    duration = str(timedelta(seconds=int(audio.info.length)))
    ET.SubElement(item, "enclosure", attrib={"url": audio_url, "length": str(os.path.getsize(os.path.join('docs', 'podcast', f"{date_str}_{mode}", 'audio.mp3'))), "type": "audio/mpeg"})
    ET.SubElement(item, "itunes:duration").text = duration

    # 格式化 XML
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = ET.fromstring(rough_string)
    xml_str = ET.tostring(reparsed, encoding='utf-8', method='xml').decode('utf-8')

    return xml_str

def save_rss(xml_str, mode):
    """保存 RSS XML"""
    output_dir = os.path.join('docs', 'rss')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'podcast_{mode}.xml')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        logger.info(f"RSS 保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存 RSS 失敗: {e}")

def send_slack_notification(mode, audio_url, analysis, strategy):
    """發送 Slack 通知"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("缺少 SLACK_WEBHOOK_URL，跳過通知")
        return
    try:
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Auto Trading Loop 完成 ✅*\nRepo: timhun/daily-podcast-stk\nRun ID: {datetime.now().strftime('%Y%m%d%H%M%S')}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{mode.upper()} 模擬摘要 ({'0050.TW' if mode == 'tw' else 'QQQ'}):*\n• Signal: {analysis.get('recommendation', 'N/A')}\n• Price: {analysis.get('target_price', 'N/A') or analysis.get('stop_loss', 'N/A')}\n• Volume Rate: N/A\n• Size: {analysis.get('position_size', 0.0)}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*週期回測:*\n• Sharpe: N/A\n• Max Drawdown: N/A\n• 策略回報: {strategy.get('return', 'N/A')}%"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*播客連結:*\n<{audio_url}|點擊收聽>"
                    }
                }
            ]
        }
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logger.info(f"Slack 通知發送成功")
    except Exception as e:
        logger.error(f"Slack 通知失敗: {e}")

def main():
    """主函數，執行推播員任務"""
    current_hour = datetime.now().hour
    if current_hour not in [6, 14]:  # 僅 6am 和 2pm 推播
        logger.info(f"當前時間 {current_hour}:00 CST 不在推播時段，跳過")
        return

    mode = 'us' if current_hour == 6 else 'tw'
    audio_url = load_upload_url(mode)
    if not audio_url:
        logger.warning(f"跳過 {mode} 推播，因缺少上傳連結")
        return

    symbol = '0050.TW' if mode == 'tw' else 'QQQ'
    analysis = load_analysis(symbol)
    strategy = load_strategy(symbol)
    if not analysis or not strategy:
        logger.warning(f"跳過 {mode} 推播，因缺少分析或策略數據")
        return

    rss_xml = generate_rss(mode, audio_url)
    save_rss(rss_xml, mode)
    send_slack_notification(mode, audio_url, analysis, strategy)

if __name__ == '__main__':
    main()
