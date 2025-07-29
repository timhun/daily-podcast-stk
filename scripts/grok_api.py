# scripts/grok_api.py
import os
import requests
import json
import logging
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GROK_API_URL = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
GROK_API_KEY = os.getenv("GROK_API_KEY")

def ask_grok(prompt: str, role: str = "user", model: str = "grok-4") -> str:
    """
    呼叫 xAI Grok API，取得純文字回應（適用 script）
    """
    if not GROK_API_KEY:
        logger.error("未找到 GROK_API_KEY 環境變數")
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
        "temperature": 0.7,
        "max_tokens": 512  # 明確指定 max_tokens
    }

    try:
        # 添加重試機制
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not reply:
            logger.error("Grok 回傳內容為空")
            raise RuntimeError("❌ Grok 回傳內容為空")
        logger.info("成功從 Grok API 獲取回應")
        return reply
    except requests.RequestException as e:
        logger.error(f"Grok API 請求失敗: {e}")
        raise

def ask_grok_json(prompt: str, role: str = "user", model: str = "grok-4") -> dict:
    """
    呼叫 xAI Grok API，取得 JSON 結構回應（會自動解析為 dict）
    """
    reply = ask_grok(prompt, role=role, model=model)
    try:
        # 使用正則表達式提取 JSON
        import re
        json_match = re.search(r'\{.*\}', reply, re.DOTALL)
        if not json_match:
            logger.error("Grok 回傳資料不包含 JSON 格式")
            raise ValueError("❌ Grok 回傳不是合法 JSON：\n" + reply)
        json_str = json_match.group(0)
        data = json.loads(json_str)
        logger.info("成功解析 JSON 資料")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗: {e}\n原始回應: {reply}")
        raise ValueError("❌ Grok 回傳不是合法 JSON：\n" + reply)
