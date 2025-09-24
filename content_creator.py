import os
import json
from xai_sdk import Client
from xai_sdk.chat import user, system
import datetime
from loguru import logger

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    
# Environment variables for xAI API
XAI_API_KEY = os.getenv("GROK_API_KEY")

def generate_script(market_data, mode, strategy_results, market_analysis):
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY not set, using fallback script")
        market = market_data.get('market', {})
        analysis = "\n".join([
            f"{symbol}: 收盤 {info.get('close', 0):.2f}, 漲跌 {info.get('change', 0):.2f}%"
            for symbol, info in market.items()
        ])
        news = market_data.get('news', [])
        news_str = "\n".join([
            f"新聞: {item.get('title', '無')} - {item.get('description', '無')}" for item in news[:3]
        ])
        sentiment = market_data.get('sentiment', {})
        sentiment_str = (
            f"市場情緒: 整體分數 {sentiment.get('overall_score', 0):.2f}, 看漲比例 {sentiment.get('bullish_ratio', 0):.2f}"
        )

        # 市場分析摘要
        market_analysis_str = "\n".join([
            f"{symbol}: 趨勢 {result.get('trend', 'NEUTRAL')}, 波動性 {result.get('volatility', 0):.2f}%, {result.get('report', '無')}"
            for symbol, result in (market_analysis or {}).items()
        ])

        # 策略摘要：挑選每個標的期望報酬最高的策略
        def summarize_best_strategies(all_results):
            lines = []
            for sym, sym_results in (all_results or {}).items():
                if not isinstance(sym_results, dict) or not sym_results:
                    continue
                best_name, best_ret = None, None
                for name, res in sym_results.items():
                    er = (res or {}).get('expected_return', 0) or 0
                    if best_ret is None or er > best_ret:
                        best_name, best_ret = name, er
                if best_name is not None:
                    lines.append(f"{sym}: 最佳策略 {best_name}, 預期回報 {best_ret:.2f}%")
            return "\n".join(lines)

        strategy_str = summarize_best_strategies(strategy_results)

        today = datetime.date.today().strftime('%Y年%m月%d日')
        return f"""
        生成 {mode.upper()} 版播客文字稿，長度控制在{config['podcast']['script_length_limit']}字內，風格專業親和，使用台灣用語。
        文字稿必須是連貫的敘述性文字，適合直接轉換成語音。不要包含任何結構標記如 '-' 或 '*'，不要包含橋段標題或解釋（如 '開場:' 或 '市場概況:'），只需生成完整的、流暢的播客內容。
        
        基於以下內容生成：
        開場白：歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        市場分析：{market_analysis_str or '無市場分析'}
        策略分析：{strategy_str or '無有效策略分析'}
        結尾：投資如馬拉松，穩健前行才能致勝。
        
        輸出應為純文字稿，無額外格式。記得你是專業的財經主播。
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

    # 策略分析：挑選每個標的期望報酬最高的策略
    def summarize_best_strategies(all_results):
        lines = []
        for sym, sym_results in (all_results or {}).items():
            if not isinstance(sym_results, dict) or not sym_results:
                continue
            best_name, best_ret = None, None
            for name, res in sym_results.items():
                er = (res or {}).get('expected_return', 0) or 0
                if best_ret is None or er > best_ret:
                    best_name, best_ret = name, er
            if best_name is not None:
                lines.append(f"{sym}: 最佳策略 {best_name}, 預期回報 {best_ret:.2f}%")
        return "\n".join(lines)

    strategy_str = summarize_best_strategies(strategy_results)

    # 市場分析
    market_analysis_str = "\n".join([f"{symbol}: 趨勢 {result['trend']}, 波動性 {result['volatility']:.2f}%, {result['report']}"
                                     for symbol, result in market_analysis.items()])
    
    today = datetime.date.today().strftime('%Y年%m月%d日')
    prompt = f"""
    生成 {mode.upper()} 版播客文字稿，長度控制在{config['podcast']['script_length_limit']}字內，風格專業親和，使用台灣用語。
    文字稿必須是連貫的敘述性文字，適合直接轉換成語音。不要包含任何結構標記如 '-' 或 '*'，不要包含橋段標題或解釋（如 '開場:' 或 '市場概況:'），只需生成完整的、流暢的播客內容。
    
    基於以下內容生成：
    開場白：歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。
    市場概況：{analysis}
    產業動態：{news_str}
    市場情緒：{sentiment_str}
    市場分析：{market_analysis_str or '無市場分析'}
    策略分析：{strategy_str or '無有效策略分析'}
    結尾：投資金句 (選用 - 科斯托蘭尼 André Kostolany)。
    
    注意 (1) 輸出應為純文字稿，無額外格式。記得你是專業的財經主播。
        (2) 不要播出股票代碼而是直接用股票名稱，如 TWII 為加權指數，2330為台積電
        (3) 不要播報技術指標數字，而是說出數字所代表的意思
        (4) 產業新聞只取半導體及AI相關
        (5) 最後要明確指出 QQQ 和 0050 的買賣策略及大盤多空方向
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
        歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。
        市場概況：{analysis}
        產業動態：{news_str}
        市場情緒：{sentiment_str}
        市場分析: {market_analysis_str or '無市場分析'}
        策略分析：{strategy_str or '無有效策略分析'}
        結尾：投資如馬拉松，穩健前行才能致勝。
        (備註：API 調用失敗，無法生成完整內容)
        """
