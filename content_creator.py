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
    """
    生成投資播客文字稿
    
    Args:
        market_data: 市場數據字典
        mode: 播客模式
        strategy_results: 策略分析結果
        market_analysis: 市場分析結果
    
    Returns:
        str: 生成的播客文字稿
    """
    
    # 共同數據處理區塊 (Common Data Processing)
    market = market_data.get('market', {})
    analysis = "\n".join([
        f"{symbol}: 收盤 {info.get('close', 0):.2f}, 漲跌 {info.get('change', 0):.2f}%"
        for symbol, info in market.items() 
        if 'close' in info and 'change' in info
    ])
    
    news = market_data.get('news', [])
    news_str = "\n".join([
        f"新聞: {item.get('title', '無')} - {item.get('description', '無')}"
        for item in news[:3]
    ]) if news else "暫無重要產業新聞"

    sentiment = market_data.get('sentiment', {})
    sentiment_str = (
        f"市場情緒: 整體分數 {sentiment.get('overall_score', 0):.2f}, "
        f"看漲比例 {sentiment.get('bullish_ratio', 0):.2f}"
    )

    market_analysis_str = "\n".join([
        f"{symbol}: 趨勢 {result.get('trend', 'NEUTRAL')}, "
        f"波動性 {result.get('volatility', 0):.2f}%, {result.get('report', '無')}"
        for symbol, result in (market_analysis or {}).items()
    ])

    def summarize_best_strategies(all_results):
        """總結最佳投資策略"""
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
        return "\n".join(lines) if lines else "暫無策略分析"

    strategy_str = summarize_best_strategies(strategy_results)
    today = datetime.date.today().strftime('%Y年%m月%d日')

    # 如果 XAI_API_KEY 未設定，使用 fallback
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY not set, using fallback script")
        return f"""歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。

市場概況：
{analysis or '暫無市場數據'}

產業動態：
{news_str}

市場情緒：
{sentiment_str}

市場分析：
{market_analysis_str or '無市場分析'}

策略分析：
{strategy_str}

投資如馬拉松，穩健前行才能致勝。感謝收聽，我們下次見。

(備註：API Key 未設定，使用簡化版本)"""

    # 構建 Prompt
    prompt = f"""生成 {mode.upper()} 投資大師文字稿，長度控制在{config['podcast']['script_length_limit']}字內，風格專業親和，使用台灣用語。

文字稿必須是連貫的敘述性文字，適合直接轉換成語音。不要包含任何結構標記如 '-' 或 '*'，不要包含橋段標題或解釋（如 '開場:' 或 '市場概況:'），只需生成完整的、流暢的播客內容。

基於以下內容生成：

開場白：歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。

市場概況：
{analysis or '暫無市場數據'}

產業動態：
{news_str}

市場情緒：
{sentiment_str}

市場分析：
{market_analysis_str or '無市場分析'}

策略分析：
{strategy_str}

結尾：投資金句（選用 - 科斯托蘭尼 André Kostolany）。

注意事項：
(1) 輸出應為純文字稿，無額外格式。記得你是專業投資大師主播。
(2) 不要播出股票代碼而是直接用股票名稱，如 TWII 為加權指數，2330為台積電。
(3) 不要播報技術指標數字，而是說出數字所代表的意思。
(4) 產業新聞只取半導體及AI相關。
(5) 最後要明確指出 QQQ 和 0050 的買賣策略及大盤多空方向。"""

    try:
        # 創建 xAI 客戶端，設定合理的 timeout
        client = Client(api_key=XAI_API_KEY, timeout=120)
        chat = client.chat.create(model="grok-3-mini")
        
        # 添加系統和用戶訊息
        chat.append(system(
            "You are Grok, a highly intelligent AI assistant created by xAI, "
            "specializing in generating professional and engaging podcast scripts in Traditional Chinese."
        ))
        chat.append(user(prompt))
        
        # 生成回應
        response = chat.sample()
        logger.info("成功生成播客文字稿")
        return response.content
        
    except TimeoutError:
        logger.error("API 請求超時")
        return generate_fallback_script(today, analysis, news_str, sentiment_str, 
                                       market_analysis_str, strategy_str, 
                                       error_msg="API 請求超時")
    except Exception as e:
        logger.error(f"API 錯誤: {str(e)}", exc_info=True)
        return generate_fallback_script(today, analysis, news_str, sentiment_str, 
                                       market_analysis_str, strategy_str, 
                                       error_msg=f"API 調用失敗: {str(e)}")


def generate_fallback_script(today, analysis, news_str, sentiment_str, 
                             market_analysis_str, strategy_str, error_msg=""):
    """
    生成備用文字稿
    
    Args:
        today: 今日日期
        analysis: 市場分析
        news_str: 新聞字串
        sentiment_str: 市場情緒
        market_analysis_str: 市場分析字串
        strategy_str: 策略字串
        error_msg: 錯誤訊息
    
    Returns:
        str: 備用文字稿
    """
    return f"""歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。

市場概況：
{analysis or '暫無市場數據'}

產業動態：
{news_str}

市場情緒：
{sentiment_str}

市場分析：
{market_analysis_str or '無市場分析'}

策略分析：
{strategy_str}

投資如馬拉松，穩健前行才能致勝。感謝收聽，我們下次見。

(備註：{error_msg or 'API 調用失敗，使用備用版本'})"""
