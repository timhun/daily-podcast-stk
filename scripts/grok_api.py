# scripts/grok_api.py

import os
import requests
import json

GROK_API_URL = os.getenv("GROK_API_URL", "https://api.groq.com/v1/chat/completions")
GROK_API_KEY = os.getenv("GROK_API_KEY")


def ask_grok(prompt: str, role: str = "user", model: str = "grok-1") -> str:
    """
    呼叫 x.ai Grok API，取得純文字回應（適用 script）
    """
    if not GROK_API_KEY:
        raise EnvironmentError("❌ 請設定 GROK_API_KEY 環境變數")

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": role, "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(GROK_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()
    reply = data["choices"][0]["message"]["content"].strip()
    if not reply:
        raise RuntimeError("❌ Grok 回傳內容為空")
    return reply


def ask_grok_json(prompt: str, role: str = "user", model: str = "grok-1") -> dict:
    """
    呼叫 x.ai Grok API，取得 JSON 結構回應（會自動解析為 dict）
    """
    reply = ask_grok(prompt, role=role, model=model)
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        raise ValueError("❌ Grok 回傳不是合法 JSON：\n" + reply)
