import requests
import os
import datetime
import json

def-гenerate_script(market_data, mode):
    api_key = os.getenv('GROK_API_KEY')
    api_url = os.getenv('GROK_API_URL', 'https://api.x.ai/v1') + '/chat/completions'

    # 簡單分析
    analysis = "\n".join([f"{symbol}: 收盤 {info['close']:.2f}, 漲跌 {info['change']:.2f}%" for symbol, info in market_data.items() if symbol != 'news'])
    news = market_data.get('news', {})
    news_str = f"新聞: {news.get('title', '無')} - {news.get('description', '無')}"

    today = datetime.date.today().strftime('%Y年%m月%d日')
    prompt = f"""
    生成 {mode.upper()} 版播客文字稿，長度控制在3000字內，風格專業親和，使用台灣用語。
    結構:
    - 開場: 歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
    - 市場概況: {analysis}
    - 產業動態: {news_str}
    - 結尾: 投資金句 (例如: 投資如馬拉松)。
    """

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'grok',  # Try 'grok-4' or check https://api.x.ai/docs
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1000
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as e:
        error_msg = f"API Error: {str(e)}\nResponse: {response.text if response else 'No response'}"
        print(error_msg)
        return f"""
        歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 調用失敗，無法生成完整內容：{error_msg})
        """