# src/strategy_llm_groq.py
import os
from groq import Groq

TEMPLATE = """你是一名量化開發者。根據以下週報摘要，輸出一段可直接被匯入的 Python 策略碼：
- 需定義 class StrategyCandidate:
- 含 staticmethod generate_signal(df: pandas.DataFrame) -> dict，回傳 {"signal": "buy/sell/hold", "size_pct": float}
- 允許使用常見技術指標（MA/RSI/BBands 等）
- 請避免依賴外部套件（除了 pandas/numpy）

週報 JSON：
{{WEEKLY_JSON}}

歷史策略績效（可選）：{{HISTORY_JSON}}
請輸出完整可執行的 Python 程式碼，不要加解說文字。
"""

def render_prompt(weekly_json: str, history_json: str = "") -> str:
    return TEMPLATE.replace("{{WEEKLY_JSON}}", weekly_json).replace("{{HISTORY_JSON}}", history_json or "[]")

def generate_strategy_with_groq(weekly_json: str, history_json: str = "") -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 GROQ_API_KEY")
    client = Groq(api_key=api_key)

    prompt = render_prompt(weekly_json, history_json)
    # 使用 OpenAI 相容 chat.completions 介面
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=3000,
    )
    code = resp.choices[0].message.content
    return code
