import os
from xai_sdk import Client
from xai_sdk.chat import user, system
import datetime
from loguru import logger

# Environment variables for xAI API
GROK_API_KEY = os.getenv("GROK_API_KEY")

def generate_script(market_data, mode):
    # Validate API key
    if not GROK_API_KEY:
        logger.error("XAI_API_KEY environment variable is not set")
        raise EnvironmentError("XAI_API_KEY environment variable is not set")

    # Market data analysis
    market = market_data.get('market', {})
    analysis = "\n".join([f"{symbol}: 收盤 {info['close']:.2f}, 漲跌 {info['change']:.2f}%"
                         for symbol, info in market.items() if 'close' in info and 'change' in info])

    # News content
    news = market_data.get('news', [])
    news_str = "\n".join([f"新聞: {item.get('title', '無')} - {item.get('description', '無')}"
                          for item in news[:3]])  # Limit to 3 news items

    # Sentiment analysis
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

    try:
        # Initialize xAI SDK client
        client = Client(
            api_key=GROK_API_KEY,
            timeout=3600  # 1 hour timeout for complex reasoning
        )

        # Create chat session with a valid model
        chat = client.chat.create(model="grok-3-mini")  # Updated to a valid model; check https://x.ai/api for latest models

        # Append system and user prompts
        chat.append(system("You are Grok, a highly intelligent AI assistant created by xAI, specializing in generating professional and engaging podcast scripts in Traditional Chinese."))
        chat.append(user(prompt))

        # Sample response
        response = chat.sample()
        logger.info("Successfully generated podcast script via xAI API")
        return response.content

    except Exception as e:
        error_msg = f"API error: {str(e)}"
        logger.error(error_msg)
        # Fallback content
        fallback_script = f"""
        歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 調用失敗，無法生成完整內容：{error_msg})
        """
        return fallback_script
