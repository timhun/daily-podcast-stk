#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os
import json
import datetime
from groq import Groq

def generate_strategy_llm(df_json: dict, history_file="strategy_history.json") -> dict:
    """
    使用 Groq LLM 生成策略 JSON
    df_json: 最新 OHLCV + 技術指標資料
    history_file: 保存歷史策略績效
    return: 策略 JSON，保證有 'regime' 欄位
    """
    # Create client instance
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    groq = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

    prompt = f"根據下列數據生成交易策略 JSON，必須包含 regime (trend/range):\n{json.dumps(df_json)}"
    
    resp = groq.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    resp_content = resp.choices[0].message.content

    try:
        strategy = json.loads(resp_content)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode failed: {e}. Response was: {resp_content}")
        strategy = {"signal": "hold", "size_pct": 0.0, "note": "LLM parse error"}

    # 確保 regime 欄位存在
    if "regime" not in strategy:
        strategy["regime"] = "trend"  # 預設 trend

    # 整理 Slack/Email 顯示格式
    summary = f"Signal: {strategy.get('signal', 'hold')}\n" \
              f"Size: {strategy.get('size_pct', 0.0)}\n" \
              f"Regime: {strategy.get('regime')}"
    strategy["summary"] = summary

    # 更新策略歷史
    today = datetime.date.today().isoformat()
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                print("[WARNING] History file corrupted or empty, resetting history.")
                history = []

    history.append({
        "date": today,
        "strategy": strategy,
        "sharpe": strategy.get("sharpe"),
        "mdd": strategy.get("mdd")
    })

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return strategy