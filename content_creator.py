import requests
import os
import datetime
import json
from loguru import logger  # 新增導入

def generate_script(market_data, mode):
    api_key = os.getenv('GROK_API_KEY')
    api_url = os.getenv('GROK_API_URL', 'https://api.x.ai/v1') + '/chat/completions'

    # 市場數據分析
    market = market_data.get('market', {})
    analysis = "\n".join([f"{symbol}: 收盤 {info['close']:.2f}, 漲跌 {info['change']:.2f}%" 
                         for symbol, info in market.items() if 'close' in info and 'change' in info])
    
    # 新聞內容
    news = market_data.get('news', [])
    news_str = "\n".join([f"新聞: {item.get('title', '無')} - {item.get('description', '無')}" 
                          for item in news[:3]])  # 限制最多 3 則新聞

    # 情緒分析
    sentiment = market_data.get('sentiment', {})
    sentiment_str = f"市場情緒: 整體分數 {sentiment.get('overall_score', 0):.2f}, 看漲比例 {sentiment.get('bullish_ratio', 0):.2f}"

    today = datetime.date.today().strftime('%Y年%m月%d日')
    prompt = f"""
    生成 {mode.upper()} 版播客文字稿，長度控制在3000字內，風格專業親和，使用台灣用語。
    結構:
    - 開場: 歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
    - 市場概況: {analysis}
    - 產業動態: {news_str}
    - 市場情緒: {sentiment_str}
    - 結尾: 投資金句 (例如: 投資如馬拉松)。
    """

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'grok',  # 可根據 https://x.ai/api 檢查最新模型
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1000
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as e:
        error_msg = f"API 錯誤: {str(e)}\n回應: {response.text if response else '無回應'}"
        logger.error(error_msg)
        return f"""
        歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 調用失敗，無法生成完整內容：{error_msg})
        """