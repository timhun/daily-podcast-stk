import json
import os
import logging
import requests

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_tw_market_data(input_file="tw_market_data.txt", output_file="market_data_tw.json"):
    # 檢查輸入檔案是否存在
    if not os.path.exists(input_file):
        logger.error(f"輸入檔案 {input_file} 不存在")
        raise FileNotFoundError(f"輸入檔案 {input_file} 不存在")

    # 讀取提示檔案
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            prompt = f.read()
        logger.info(f"成功讀取提示檔案: {input_file}")
    except Exception as e:
        logger.error(f"讀取檔案 {input_file} 失敗: {e}")
        raise

    # 初始化 API 請求
    try:
        api_key = os.getenv("GROK_API_KEY")
        api_url = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
        if not api_key:
            logger.error("未找到 GROK_API_KEY 環境變數")
            raise ValueError("請設置 GROK_API_KEY 環境變數")

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
        response.raise_for_status()  # 檢查 HTTP 錯誤
        result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("成功從 Grok 獲取回應")
    except requests.RequestException as e:
        logger.error(f"Grok API 請求失敗: {e}")
        raise

    # 解析 JSON
    try:
        json_start = result.find("{")
        if json_start == -1:
            logger.error("Grok 回傳資料不包含 JSON 格式")
            raise ValueError("Grok 回傳資料不包含 JSON 格式")
        json_str = result[json_start:]
        data = json.loads(json_str)
        logger.info("成功解析 JSON 資料")
    except Exception as e:
        logger.error(f"JSON 解析失敗: {e}\n原始回應: {result}")
        raise RuntimeError(f"❌ Grok 回傳格式錯誤: {e}")

    # 檢查輸出路徑
    output_dir = os.path.dirname(output_file) or "."
    if not os.access(output_dir, os.W_OK):
        logger.error(f"無法寫入輸出路徑: {output_dir}")
        raise PermissionError(f"無法寫入輸出路徑: {output_dir}")

    # 儲存 JSON
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已儲存 {output_file}")
    except Exception as e:
        logger.error(f"儲存檔案 {output_file} 失敗: {e}")
        raise

if __name__ == "__main__":
    try:
        fetch_tw_market_data()
    except Exception as e:
        logger.critical(f"程式執行失敗: {e}")
        raise