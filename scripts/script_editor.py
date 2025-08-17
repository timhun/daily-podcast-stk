import pandas as pd
import json
import os
from datetime import datetime
import logging
import requests
from feedparser import parse

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置 Grok API 和 RSS 來源
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.grok.xai.com/v1/generate_script"  # 假設的 API 端點
RSS_URL = "https://tw.stock.yahoo.com/rss?category=news"

def load_config():
    """載入配置檔案 config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        logger.error(f"缺少配置檔案: {config_file}")
        raise FileNotFoundError(f"缺少配置檔案: {config_file}")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
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

def fetch_rss_news():
    """從 RSS 抓取最新新聞，篩選《經濟》、《半導體》標題"""
    try:
        response = requests.get(RSS_URL, timeout=10)
        response.raise_for_status()
        feed = parse(response.text)
        news = []
        for entry in feed.entries[:10]:  # 取前 10 則作為候選
            title = entry.title
            if any(keyword in title for keyword in ['經濟', '半導體']):
                news.append({'title': title, 'link': entry.link, 'published': entry.published})
            if len(news) >= 3:
                break
        logger.info(f"抓取到 {len(news)} 則相關新聞")
        return news[:3]  # 確保最多 3 則
    except Exception as e:
        logger.error(f"RSS 抓取失敗: {e}")
        return []

def generate_script(symbol, analysis, news, mode):
    """生成 podcast 文字稿模板"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M CST")
    latest = analysis.get('recommendation', '持倉')
    price = analysis.get('target_price', 'N/A') if latest == '買入' else analysis.get('stop_loss', 'N/A')
    position = analysis.get('position_size', 0.0)
    risk_note = analysis.get('risk_note', '無風險數據')

    base_script = f"""嗨，親愛的聽眾朋友們，大家好！歡迎來到今天的市場分析時光！現在是 {now}，我們來看看{('台股' if mode == 'tw' else '美股')}動態吧！

### 市場快訊
{('台股方面，0050 最新建議是 ' + latest + '，目標價/停損價約 ' + str(price) + ' 元，倉位 ' + str(position) + '。' if mode == 'tw' else '美股方面，QQQ 最新建議是 ' + latest + '，目標價/停損價約 ' + str(price) + ' 美元，倉位 ' + str(position) + '。')}
市場風險提示：{risk_note}。

### 市場新聞
最新新聞焦點：
"""
    for i, item in enumerate(news, 1):
        base_script += f"- {i}. {item['title']} ({item['published']}) [詳情]({item['link']})\n"

    base_script += """### 總結與建議
總結來說，今天{'0050' if mode == 'tw' else 'QQQ'}走勢平穩，建議{'買入並設定目標' if latest == '買入' else '賣出或持倉觀察'}。量是因，價是果，紀律賺大錢！我是你的財經導航員，謝謝收聽，下次見！

（免責聲明：Grok 不是財務顧問，請諮詢專業人士。）"""

    return base_script

def save_script(script, mode):
    """保存文字稿"""
    output_dir = os.path.join('docs', 'podcast', datetime.now().strftime("%Y%m%d") + '_' + mode)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'script.txt')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info(f"文字稿保存至 {output_path}")
    except Exception as e:
        logger.error(f"保存文字稿失敗: {e}")

def improve_with_grok(script):
    """使用 Grok API 優化文字稿"""
    if not GROK_API_KEY:
        logger.warning("缺少 GROK_API_KEY，跳過優化")
        return script
    try:
        response = requests.post(GROK_API_URL, json={'script': script}, headers={'Authorization': f'Bearer {GROK_API_KEY}'})
        response.raise_for_status()
        improved_script = response.json().get('improved_script', script)
        logger.info("Grok API 優化文字稿成功")
        return improved_script
    except Exception as e:
        logger.error(f"Grok API 優化失敗: {e}")
        return script

def main():
    """主函數，執行文字編輯"""
    symbols = load_config()
    mode = 'tw' if datetime.now().hour == 14 else 'us'  # 2pm 台股，6am 美股
    symbol = '0050.TW' if mode == 'tw' else 'QQQ'

    analysis = load_analysis(symbol)
    if analysis is None:
        logger.warning(f"跳過 {mode} 文字稿生成，因分析數據缺失")
        return

    news = fetch_rss_news()
    script = generate_script(symbol, analysis, news, mode)
    improved_script = improve_with_grok(script)
    save_script(improved_script, mode)

if __name__ == '__main__':
    main()
