# scripts/grok_api.py
import os
import requests
import json
import logging
import random
import threading
import time
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

GROK_API_URL = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# Global concurrency and rate limiting controls
_grok_max_concurrency = int(os.getenv("GROK_MAX_CONCURRENCY", "2"))
_grok_min_interval_sec = float(os.getenv("GROK_MIN_INTERVAL_SEC", "0.5"))
_grok_semaphore = threading.Semaphore(_grok_max_concurrency)
_grok_last_request_ts = 0.0
_grok_last_ts_lock = threading.Lock()

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
        "max_tokens": 1024,  # 增加 max_tokens 以確保完整回應
        "stream": False
    }

    # Prepare session with connection retries only (we handle HTTP status retries ourselves)
    session = requests.Session()
    connection_retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status=0,
        allowed_methods=None
    )
    session.mount("https://", HTTPAdapter(max_retries=connection_retries))

    # Log payload for debugging (size and partial content)
    payload_str = json.dumps(payload)
    logger.info(
        f"Preparing Grok API request. Payload size: {len(payload_str)} bytes. Prompt preview: {prompt[:100]}..."
    )

    max_attempts = int(os.getenv("GROK_MAX_RETRIES", "7"))
    base_backoff = float(os.getenv("GROK_BACKOFF_BASE_SEC", "1.5"))

    # Concurrency limit
    _grok_semaphore.acquire()
    try:
        # Min-interval throttling
        with _grok_last_ts_lock:
            now = time.time()
            elapsed = now - _grok_last_request_ts
            if elapsed < _grok_min_interval_sec:
                sleep_time = _grok_min_interval_sec - elapsed
            else:
                sleep_time = 0.0
        if sleep_time > 0:
            time.sleep(sleep_time)

        for attempt in range(max_attempts):
            try:
                # Timeout: connect=10s, read=50s
                response = session.post(
                    GROK_API_URL, headers=headers, json=payload, timeout=(10, 50)
                )
                # Update last request timestamp
                with _grok_last_ts_lock:
                    global _grok_last_request_ts
                    _grok_last_request_ts = time.time()

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            wait_sec = float(retry_after)
                        except ValueError:
                            wait_sec = base_backoff * (2 ** attempt)
                    else:
                        wait_sec = base_backoff * (2 ** attempt)
                    # Add jitter up to 30% of wait
                    wait_sec = min(120.0, wait_sec) + random.uniform(0, 0.3 * max(0.5, wait_sec))
                    logger.warning(
                        f"Grok rate-limited (429). Attempt {attempt + 1}/{max_attempts}. Waiting {wait_sec:.2f}s before retry."
                    )
                    time.sleep(wait_sec)
                    continue

                if 500 <= response.status_code < 600:
                    wait_sec = min(60.0, base_backoff * (2 ** attempt)) + random.uniform(0, 0.5)
                    logger.warning(
                        f"Grok server error {response.status_code}. Attempt {attempt + 1}/{max_attempts}. Waiting {wait_sec:.2f}s before retry."
                    )
                    time.sleep(wait_sec)
                    continue

                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices or not choices[0].get("message", {}).get("content"):
                    logger.error(f"Grok 回傳無效內容: {data}")
                    raise RuntimeError("❌ Grok 回傳內容為空或無效")
                reply = choices[0]["message"]["content"].strip()
                logger.info("成功從 Grok API 獲取回應")
                return reply
            except requests.exceptions.ReadTimeout as e:
                if attempt < max_attempts - 1:
                    wait_sec = min(60.0, base_backoff * (2 ** attempt)) + random.uniform(0, 0.5)
                    logger.warning(
                        f"Grok API 讀取逾時 (attempt {attempt + 1}/{max_attempts}). Retrying in {wait_sec:.2f}s. Error: {e}"
                    )
                    time.sleep(wait_sec)
                    continue
                logger.error(f"Grok API 請求超時: {e}. 已達最大重試次數。")
                raise
            except requests.RequestException as e:
                # Network-level issues (not HTTP status) -> retry with backoff
                if attempt < max_attempts - 1:
                    wait_sec = min(60.0, base_backoff * (2 ** attempt)) + random.uniform(0, 0.5)
                    logger.warning(
                        f"Grok API 請求失敗 (attempt {attempt + 1}/{max_attempts}). Retrying in {wait_sec:.2f}s. Error: {e}"
                    )
                    time.sleep(wait_sec)
                    continue
                logger.error(f"Grok API 請求失敗: {e}")
                raise
        # If we exit the loop, raise a final error
        raise RuntimeError("❌ Grok API 多次重試後仍失敗")
    finally:
        _grok_semaphore.release()
        
def ask_grok_json(prompt: str, role: str = "user", model: str = "grok-4") -> dict:
    """
    呼叫 xAI Grok API，取得 JSON 結構回應（會自動解析為 dict）
    """
    reply = ask_grok(prompt, role=role, model=model)
    try:
        # 使用正則表達式提取 JSON，優先嘗試 ```json 代碼區塊
        import re
        fenced_match = re.search(r"```json\s*([\s\S]*?)\s*```", reply, re.IGNORECASE)
        if fenced_match:
            json_str = fenced_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', reply, re.DOTALL)
            if not json_match:
                logger.error("Grok 回傳資料不包含 JSON 格式")
                raise ValueError(f"❌ Grok 回傳不是合法 JSON：\n{reply[:500]}")
            json_str = json_match.group(0)
        data = json.loads(json_str)
        logger.info("成功解析 JSON 資料")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失敗: {e}\n原始回應(截斷): {reply[:500]}")
        raise ValueError(f"❌ Grok 回傳不是合法 JSON：\n{reply[:500]}")
