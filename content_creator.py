import os
import json
from loguru import logger
import datetime

# 新的統一 NIM API（支援多 provider 自動 failover）
from nim_api import call_nim, optimize_script_with_nim

# 載入 config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# ============================================================================
# 舊的多 Provider 函數已移除
# 統一使用 nim_api.py 的 call_nim() 函數
# 支援自動 failover、任務分類選模型、速率限制
# ============================================================================

def generate_script_with_llm(prompt):
    """使用 NIM API 生成文字稿（自動選擇最佳模型）"""
    logger.info("開始使用 NIM API 生成文字稿...")
    
    # 使用 script 任務類型，自動選擇適合的模型
    result = call_nim(
        prompt=prompt,
        task_type="script",
        temperature=0.7,
        max_tokens=3000
    )
    
    if result:
        logger.success("✓ NIM API 成功生成文字稿")
        return result
    
    logger.error("NIM API 失敗")
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

市場情緒：(no data read out directly, 解讀多空方向即可）
{sentiment_str}

市場分析：
{market_analysis_str or '無市場分析'}

策略分析： (只要show QQQ 或 0050.TW)
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
