import json
import os
import logging
import requests
from pathlib import Path

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_tw_market_data(input_file="tw_market_data.txt", output_file_relative="../docs/podcast/market_data_tw.json"):
    # 取得絕對路徑
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / input_file
    output_path = (script_dir / output_file_relative).resolve()

    # 檢查輸入檔案是否存在
    if not input_path.exists():
        logger.error(f"❌ 輸入檔案 {input_path} 不存在")
        raise FileNotFoundError(f"輸入檔案 {input_path} 不存在")

    # 讀取 Prompt
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            prompt = f.read()
        logger.info(f"📄 成功讀取提示檔案: {input_path}")
    except Exception as e:
        logger.error(f"❌ 讀取檔案失敗: {e}")
        raise

    # 呼叫 Grok API
    try:
        api_key = os.getenv("GROK_API_KEY")
        api_url = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
        if not api_key:
            raise ValueError("請設定 GROK_API_KEY 環境變數")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3-beta",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("✅ 成功從 Grok 獲取回應")
    except requests.RequestException as e:
        logger.error(f"❌ Grok API 請求失敗: {e}")
        raise

    # 解析 JSON 格式
    try:
        json_start = result.find("{")
        if json_start == -1:
            raise ValueError("Grok 回傳內容不含 JSON")
        json_str = result[json_start:]
        data = json.loads(json_str)
        logger.info("📊 成功解析 JSON 資料")
    except Exception as e:
        logger.error(f"❌ 解析 JSON 失敗: {e}\n原始回應: {result}")
        raise

    # 確保輸出資料夾存在
    os.makedirs(output_path.parent, exist_ok=True)

    # 儲存 JSON 檔案
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已成功儲存 JSON 至 {output_path}")
    except Exception as e:
        logger.error(f"❌ 儲存 JSON 失敗: {e}")
        raise

if __name__ == "__main__":
    try:
        fetch_tw_market_data()
    except Exception as e:
        logger.critical(f"🚨 程式執行失敗: {e}")
        raise