import requests
import json
from datetime import datetime
from fetch_data import fetch_indices, fetch_crypto, fetch_gold, fetch_top_stocks, fetch_quote
from logger import setup_logger, log_error_and_notify

logger = setup_logger()

def generate_podcast_script(xai_api_key, cmc_api_key):
    try:
        with open('data/tw_phrases.json', 'r', encoding='utf-8') as f:
            tw_phrases = json.load(f)
        
        indices = fetch_indices()
        btc = fetch_crypto(cmc_api_key)
        gold = fetch_gold()
        stocks = fetch_top_stocks()
        quote = fetch_quote()
        date = datetime.now().strftime('%Y年%m月%d日')

        # Grok API 提示，包含新聞抓取
        prompt = f"""
你是一位親切自然的台灣中年男性財經播客主，節目名稱《大叔說財經科技投資》。請生成一篇約 1500-1800 字的 Podcast 腳本，語氣專業但接地氣，使用台灣慣用語（如「我們」、「火紅」、「穩穩賺」），語速適合 1.3 倍播放，日期為 {date}。腳本結構如下：

1. 開場白：介紹日期與節目內容（美股、加密貨幣、黃金、熱門股、AI/經濟新聞、金句）。
2. 美股四大指數：道瓊 (^DJI: {indices['^DJI']['close']} 點, {'漲' if indices['^DJI']['change'] >= 0 else '跌'} {abs(indices['^DJI']['change'])}%)、納斯達克 (^IXIC: {indices['^IXIC']['close']} 點, {'漲' if indices['^IXIC']['change'] >= 0 else '跌'} {abs(indices['^IXIC']['change'])}%)、標普500 (^GSPC: {indices['^GSPC']['close']} 點, {'漲' if indices['^GSPC']['change'] >= 0 else '跌'} {abs(indices['^GSPC']['change'])}%)、費城半導體 (^SOX: {indices['^SOX']['close']} 點, {'漲' if indices['^SOX']['change'] >= 0 else '跌'} {abs(indices['^SOX']['change'])}%)，每項簡短分析，融入正面（{tw_phrases['positive']}）或負面（{tw_phrases['negative']}）用語。
3. QQQ與SPY ETF：QQQ ({indices['QQQ']['close']}, {'漲' if indices['QQQ']['change'] >= 0 else '跌'} {abs(indices['QQQ']['change'])}%)、SPY ({indices['SPY']['close']}, {'漲' if indices['SPY']['change'] >= 0 else '跌'} {abs(indices['SPY']['change'])}%)，簡短分析。
4. 比特幣與黃金期貨：比特幣 ({btc['price']} 美元, {'漲' if btc['change'] >= 0 else '跌'} {abs(btc['change'])}%)、黃金 ({gold['price']} 美元/盎司, {'漲' if gold['change'] >= 0 else '跌'} {abs(gold['change'])}%)，簡短分析。
5. Top 5 熱門股：{', '.join(stocks)}，分析資金流向，融入 {tw_phrases['analysis']}。
6. AI 新聞：搜尋昨日與 AI 相關的最新新聞，提供標題與 100 字摘要，簡短評論，確保與台灣聽眾相關。
7. 總體經濟新聞：搜尋昨日美國經濟新聞，提供標題與 100 字摘要，簡短評論，確保與台灣聽眾相關。
8. 每日投資金句：{quote['text']} —— {quote['author']}，搭配建議。
9. 結語：總結，融入 {tw_phrases['closing']}。

請確保語氣親切、專業，融入台灣慣用語，總長約 15 分鐘播出時間，新聞來源可靠並標明出處。
"""

        headers = {
            'Authorization': f'Bearer {xai_api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'grok-3',
            'prompt': prompt,
            'max_tokens': 2000,
            'temperature': 0.7
        }
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=payload)
        response.raise_for_status()
        script = response.json()['choices'][0]['message']['content']

        with open('data/script.txt', 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info("Podcast script generated successfully via Grok API")
        return script
    except Exception as e:
        log_error_and_notify(f"Error generating script with Grok API: {str(e)}", os.getenv('SLACK_WEBHOOK_URL'))
