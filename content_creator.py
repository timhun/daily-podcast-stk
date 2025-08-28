import os
import json
from xai_sdk import Client
from xai_sdk.chat import user, system
import datetime
from loguru import logger

# Environment variables for xAI API
XAI_API_KEY = os.getenv("GROK_API_KEY")

def generate_script(market_data, mode, strategy_results):
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY not set, using fallback script")
        market = market_data.get('market', {})
        analysis = "\n".join([f"{symbol}: 收盤 {info['close']:.2f}, 漲跌 {info['change']:.2f}%"
                             for symbol, info in market.items() if 'close' in info and 'change' in info])
        news = market_data.get('news', [])
        news_str = "\n".join([f"新聞: {item.get('title', '無')} - {item.get('description', '無')}"
                              for item in news[:3]])
        sentiment = market_data.get('sentiment', {})
        sentiment_str = f"市場情緒: 整體分數 {sentiment.get('overall_score', 0):.2f}, 看漲比例 {sentiment.get('bullish_ratio', 0):.2f}"
        strategy_str = "\n".join([f"{symbol}: 最佳策略 {result['winning_strategy']['name']}, 夏普比率 {result['winning_strategy']['sharpe_ratio']:.2f}"
                                 for symbol, result in strategy_results.items()])
        today = datetime.date.today().strftime('%Y年%m月%d日')
        return f"""
        歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        策略分析：{strategy_str}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 金鑰未設置，使用後備腳本)
        """

    # 市場數據分析
    market = market_data.get('market', {})
    analysis = "\n".join([f"{symbol}: 收盤 {info['close']:.2f}, 漲跌 {info['change']:.2f}%"
                         for symbol, info in market.items() if 'close' in info and 'change' in info])
    
    # 新聞內容
    news = market_data.get('news', [])
    news_str = "\n".join([f"新聞: {item.get('title', '無')} - {item.get('description', '無')}"
                          for item in news[:3]])

    # 情緒分析
    sentiment = market_data.get('sentiment', {})
    sentiment_str = f"市場情緒: 整體分數 {sentiment.get('overall_score', 0):.2f}, 看漲比例 {sentiment.get('bullish_ratio', 0):.2f}"

    # 策略分析
    strategy_str = "\n".join([f"{symbol}: 最佳策略 {result['winning_strategy']['name']}, 夏普比率 {result['winning_strategy']['sharpe_ratio']:.2f}, 預期回報 {result['winning_strategy']['expected_return']:.2f}%"
                             for symbol, result in strategy_results.items()])

    today = datetime.date.today().strftime('%Y年%m月%d日')
    prompt = f"""
    生成 {mode.upper()} 版播客文字稿，長度控制在3000字內，風格專業親和，使用台灣用語。
    結構:
    - 開場: 歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
    - 市場概況: {analysis}
    - 產業動態: {news_str}
    - 市場情緒: {sentiment_str}
    - 策略分析: {strategy_str}
    - 結尾: 投資金句 (例如: 投資如馬拉松)。
    """

    try:
        client = Client(api_key=XAI_API_KEY, timeout=3600)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system("You are Grok, a highly intelligent AI assistant created by xAI, specializing in generating professional and engaging podcast scripts in Traditional Chinese."))
        chat.append(user(prompt))
        response = chat.sample()
        logger.info("成功生成播客文字稿")
        return response.content
    except Exception as e:
        logger.error(f"API 錯誤: {str(e)}")
        return f"""
        歡迎收聽《幫幫忙說財經科技投資》，我是幫幫忙 AI。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        策略分析：{strategy_str}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 調用失敗，無法生成完整內容)
        """