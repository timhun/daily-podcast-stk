# scripts/grok_api.py
import os
import logging

logger = logging.getLogger(__name__)

def suggest_params(strategy_summary: dict) -> dict:
    """
    若設 GROK_API_KEY，這裡可串接你實際的 Grok/Groq API。
    目前：若沒有 key，回傳輕度建議；有 key 也只是示意（避免在 CI 卡住）。
    """
    key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
    if not key:
        return {"note": "no_api_key", "suggestion": {"volume_multiplier": 1.3, "rf_thresh": 0.53}}
    # 真正串接：你可以在此用 requests 呼叫你的 LLM 端點
    # 這裡仍回傳同樣建議，避免打外網在 CI 失敗
    return {"note": "stubbed_call", "suggestion": {"volume_multiplier": 1.3, "rf_thresh": 0.53}}