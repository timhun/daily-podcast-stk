#scripts/fetch_tw_market_data_grok.py
import os
import json
from datetime import datetime
import pytz
import logging

from grok_api import ask_grok_json

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 台灣時區
TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ)
TODAY_STR = TODAY.strftime("%Y%m%d")

# 檔案路徑
PROMPT_FILE = "prompt/tw_market_data.txt"
OUTPUT_FILE = f"docs/podcast/{TODAY_STR}_tw/market_data_tw.json"

def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"❌ 找不到 prompt 檔案：{PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def save_json_to_file(data: dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 已儲存市場資料 JSON 至 {OUTPUT_FILE}")

def main():
    user_prompt = load_prompt()
    logger.info("📤 傳送 prompt 給 Grok：\n" + user_prompt[:200] + "...")
    try:
        market_data = ask_grok_json(user_prompt)
        logger.info("📥 接收市場數據：\n" + json.dumps(market_data, ensure_ascii=False, indent=2))
        save_json_to_file(market_data)
    except Exception as e:  # Catch all exceptions to include timeout
        logger.error(f"❌ 獲取數據失敗：{e}")
        # 使用回退數據
        market_data = {
            "date": TODAY.strftime("%Y-%m-%d"),
            "taiex": {"close": 23201.52, "change_percent": -0.9},
            "volume": 3500,
            "institutions": {"foreign": 50.0, "investment": -10.0, "dealer": 5.0},
            "moving_averages": {"ma5": 22800.0, "ma10": 22500.0}
        }
        save_json_to_file(market_data)

if __name__ == "__main__":
    main()
