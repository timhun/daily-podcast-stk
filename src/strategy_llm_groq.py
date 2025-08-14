#!/usr/bin/env python3
# src/strategy_llm_groq.py
import os
import json
import datetime
from groq import GroqClient  # 假設你用 Groq SDK

def generate_strategy_llm(df_json: dict, history_file="strategy_history.json") -> dict:
    """
    使用 Groq LLM 生成策略 JSON
    df_json: 最新 OHLCV + 技術指標資料
    history_file: 保存歷史策略績效
    return: 策略 JSON
    """
    client = GroqClient(api_key=os.environ.get("GROQ_API_KEY"))
    model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

    prompt = f"根據下列數據生成交易策略 JSON:\n{json.dumps(df_json)}"
    resp = client.run(model=model, prompt=prompt)
    
    try:
        strategy = json.loads(resp)
    except Exception:
        strategy = {"signal": "hold", "size_pct": 0.0, "note": "LLM parse error"}

    # 更新策略歷史
    today = datetime.date.today().isoformat()
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    history.append({
        "date": today,
        "strategy": strategy,
        "sharpe": strategy.get("sharpe", None),
        "mdd": strategy.get("mdd", None)
    })
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return strategy
