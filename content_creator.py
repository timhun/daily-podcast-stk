import os
import json
from loguru import logger
import datetime

# 支援多種 LLM 供應商
XAI_API_KEY = os.getenv("GROK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("GROQ_API_KEY")

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def call_xai_api(prompt):
    """呼叫 xAI Grok API"""
    try:
        from xai_sdk import Client
        from xai_sdk.chat import user, system
        
        client = Client(api_key=XAI_API_KEY, timeout=120)
        chat = client.chat.create(model="grok-3-mini")
        chat.append(system(
            "You are Grok, a highly intelligent AI assistant created by xAI, "
            "specializing in generating professional and engaging podcast scripts in Traditional Chinese."
        ))
        chat.append(user(prompt))
        response = chat.sample()
        logger.info("成功使用 xAI API 生成文字稿")
        return response.content
    except Exception as e:
        error_msg = str(e).replace('{', '{{').replace('}', '}}')
        logger.warning(f"xAI API 失敗: {error_msg}")
        raise

def call_openai_api(prompt):
    """呼叫 OpenAI API"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 使用較便宜的模型
            messages=[
                {"role": "system", "content": "你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        logger.info("成功使用 OpenAI API 生成文字稿")
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e).replace('{', '{{').replace('}', '}}')
        logger.warning(f"OpenAI API 失敗: {error_msg}")
        raise

def call_anthropic_api(prompt):
    """呼叫 Anthropic Claude API"""
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # 使用較便宜的模型
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system="你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"
        )
        logger.info("成功使用 Anthropic API 生成文字稿")
        return message.content[0].text
    except Exception as e:
        error_msg = str(e).replace('{', '{{').replace('}', '}}')
        logger.warning(f"Anthropic API 失敗: {error_msg}")
        raise

def generate_script_with_llm(prompt):
    """
    使用多個 LLM 供應商生成文字稿（自動備援）
    
    優先順序: xAI -> OpenAI -> Anthropic -> Fallback
    """
    # 嘗試 xAI
    if XAI_API_KEY:
        try:
            return call_xai_api(prompt)
        except Exception:
            logger.info("xAI 不可用，嘗試其他供應商...")
    
    # 嘗試 OpenAI
    if OPENAI_API_KEY:
        try:
            return call_openai_api(prompt)
        except Exception:
            logger.info("OpenAI 不可用，嘗試其他供應商...")
    
    # 嘗試 Anthropic
    if ANTHROPIC_API_KEY:
        try:
            return call_anthropic_api(prompt)
        except Exception:
            logger.info("Anthropic 不可用，使用本地備用方案...")
    
    # 所有 API 都失敗，返回 None
    logger.warning("所有 LLM API 皆不可用")
    return None

def generate_script(market_data, mode, strategy_results, market_analysis):
    """生成投資播客文字稿（多 LLM 備援版本）"""
    
    # 數據處理（與原程式碼相同）
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

    # 嘗試使用 LLM 生成
    script = generate_script_with_llm(prompt)
    
    if script:
        return script
    
    # 所有 API 都失敗，使用本地備用方案
    logger.warning("使用本地備用文字稿")
    return generate_fallback_script(today, analysis, news_str, sentiment_str, 
                                   market_analysis_str, strategy_str, 
                                   error_msg="所有 LLM API 皆不可用")

def generate_fallback_script(today, analysis, news_str, sentiment_str, 
                             market_analysis_str, strategy_str, error_msg=""):
    """生成備用文字稿"""
    return f"""歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。

讓我們來看看今天的市場狀況。{analysis or '今日市場數據暫時無法取得'}

在產業動態方面，{news_str}

{sentiment_str}

市場分析顯示，{market_analysis_str or '今日市場分析資料尚未完整'}

根據我們的策略分析，{strategy_str}

投資就像馬拉松，不是短跑衝刺。保持穩健的投資策略，長期來看才能獲得穩定的回報。感謝收聽今天的節目，我們下次見。

(系統備註：{error_msg or 'API 調用失敗，使用備用版本'})"""
