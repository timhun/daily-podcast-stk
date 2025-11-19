import os
import json
from loguru import logger
import datetime

# 支援多種 LLM 供應商
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def call_gemini_api(prompt):
    """呼叫 Google Gemini API"""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY 未設置")
        return None
    
    try:
        from google import genai
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        
        logger.info("成功使用 Gemini API 生成文字稿")
        return response.text
    except ImportError as e:
        logger.warning(f"Gemini API 導入失敗: {e}")
        return None
    except Exception as e:
        logger.warning(f"Gemini API 失敗: {type(e).__name__}: {str(e)}")
        return None

def call_openrouter_api(prompt):
    """呼叫 OpenRouter API"""
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY 未設置")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",  # 使用免費的 Gemini 模型
            messages=[
                {"role": "system", "content": "你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=120
        )
        logger.info("成功使用 OpenRouter API 生成文字稿")
        return response.choices[0].message.content
    except ImportError as e:
        logger.warning(f"OpenRouter API 導入失敗: {e}")
        return None
    except Exception as e:
        logger.warning(f"OpenRouter API 失敗: {type(e).__name__}: {str(e)}")
        return None

def call_xai_api(prompt):
    """呼叫 xAI Grok API"""
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY 未設置")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=120
        )
        logger.info("成功使用 xAI API 生成文字稿")
        return response.choices[0].message.content
    except ImportError as e:
        logger.warning(f"xAI API 導入失敗: {e}")
        return None
    except Exception as e:
        logger.warning(f"xAI API 失敗: {type(e).__name__}: {str(e)}")
        return None

def call_openai_api(prompt):
    """呼叫 OpenAI API"""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 未設置")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=120)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        logger.info("成功使用 OpenAI API 生成文字稿")
        return response.choices[0].message.content
    except ImportError as e:
        logger.warning(f"OpenAI API 導入失敗: {e}")
        return None
    except Exception as e:
        logger.warning(f"OpenAI API 失敗: {type(e).__name__}: {str(e)}")
        return None

def call_groq_api(prompt):
    """呼叫 Groq API"""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY 未設置")
        return None
    
    try:
        from groq import Groq
        
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "你是一位專業的投資播客主播，擅長用親和的語氣分析市場動態。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        logger.info("成功使用 Groq API 生成文字稿")
        return response.choices[0].message.content
    except ImportError as e:
        logger.warning(f"Groq API 導入失敗: {e}")
        return None
    except Exception as e:
        logger.warning(f"Groq API 失敗: {type(e).__name__}: {str(e)}")
        return None

def generate_script_with_llm(prompt):
    """嘗試使用多 LLM 生成文字稿"""
    
    # 定義 API 順序（按優先級）
    llm_configs = [
        ("Gemini", call_gemini_api),
        ("OpenRouter", call_openrouter_api),
        ("Groq", call_groq_api),
        ("OpenAI", call_openai_api),
        ("xAI", call_xai_api)
    ]
    
    logger.info("開始嘗試使用 LLM API 生成文字稿...")
    
    for name, func in llm_configs:
        try:
            logger.info(f"嘗試使用 {name} API...")
            result = func(prompt)
            if result:
                logger.success(f"✓ {name} API 成功生成文字稿")
                return result
            else:
                logger.warning(f"✗ {name} API 返回空結果")
        except Exception as e:
            logger.error(f"✗ {name} API 異常: {type(e).__name__}: {str(e)}")
            continue
    
    logger.error("所有 LLM API 皆不可用")
    return None

def generate_script(market_data, mode, strategy_results, market_analysis):
    """生成投資播客文字稿（多 LLM 備援版本）"""
    
    # 數據處理
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
            if not isinstance(sym_results, dict):
                continue
            best_name = sym_results.get('strategy', 'god_system')
            expected_return = sym_results.get('expected_return', 0)
            position = sym_results.get('signals', {}).get('position', 'NEUTRAL')
            chart_url = sym_results.get('best', {}).get('chart_url')

            strategy_details = []
            for strat_name, strat_result in (sym_results.get('strategies') or {}).items():
                strat_return = strat_result.get('expected_return', 0)
                strat_position = strat_result.get('signals', {}).get('position', 'NEUTRAL')
                strategy_details.append(f"{strat_name} 回報 {strat_return:.2f}% 訊號 {strat_position}")
            detail_text = "；".join(strategy_details) if strategy_details else "暫無策略結果"
            
            summary_line = (
                f"{sym}: 最佳策略 {best_name}，預期回報 {expected_return:.2f}%，訊號 {position}。"
                f"策略對戰結果：{detail_text}"
            )
            if chart_url:
                summary_line += f"\n策略圖表: {chart_url}"
            lines.append(summary_line)

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

策略分析： (只要談QQQ 或 0050.TW)
{strategy_str}

結尾：投資金句（選用 - 科斯托蘭尼 André Kostolany）。

注意事項：
(1) 輸出應為純文字稿，無額外格式。記得你是專業投資大師主播。
(2) 不要播出股票代碼而是直接用股票名稱，如 TWII 為加權指數，2330為台積電。
(3) 不要播報技術指標數字，而是說出數字所代表的意思。不用播報個股報價。
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
