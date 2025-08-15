#!/usr/bin/env python3
import os, json, datetime
from groq import Groq

def generate_strategy_llm(df_json, history_file="strategy_history.json", target_return=None):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    groq = Groq(api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

    prompt = f"生成台股策略 JSON，目標報酬率={target_return}\n數據={json.dumps(df_json)}"
    resp = groq.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    resp_content = resp.choices[0].message.content
    print("[DEBUG] LLM raw response:", resp_content)

    try:
        strategy = json.loads(resp_content)
    except json.JSONDecodeError:
        strategy = {"signal": "hold", "size_pct": 0, "note": "LLM parse error"}

    # 更新歷史
    today = datetime.date.today().isoformat()
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
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