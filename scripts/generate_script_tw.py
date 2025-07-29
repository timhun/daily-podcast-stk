import os
import json
from datetime import datetime
import pytz

from utils_podcast_tw import get_today_tw_ymd_str, is_weekend_tw, load_prompt_template

TODAY = get_today_tw_ymd_str()
MODE = "tw"

BASE_DIR = f"docs/podcast/{TODAY}_{MODE}"
os.makedirs(BASE_DIR, exist_ok=True)

# 檔案路徑
MARKET_DATA_FILE = f"{BASE_DIR}/market_data_tw.json"
SIGNAL_FILE = f"{BASE_DIR}/bullish_signal_tw.txt"
AI_TOPIC_FILE = "ai_topic.txt"  # 可選
OUTPUT_SCRIPT = f"{BASE_DIR}/script.txt"

# Prompt 檔案選擇
PROMPT_FILE = "prompt/tw_weekend.txt" if is_weekend_tw() else "prompt/tw.txt"

def load_text_file(filepath: str) -> str:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    else:
        return ""

def main():
    # 讀取 prompt 模板
    prompt_template = load_prompt_template(PROMPT_FILE)

    # 讀取資料
    try:
        with open(MARKET_DATA_FILE, "r", encoding="utf-8") as f:
            market_data = json.load(f)
    except Exception:
        raise FileNotFoundError(f"❌ 找不到市場資料 JSON：{MARKET_DATA_FILE}")

    bullish_signal = load_text_file(SIGNAL_FILE)
    ai_topic = load_text_file(AI_TOPIC_FILE)

    # 組裝 prompt
    today_display = datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y年%m月%d日")
    market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)

    script_text = prompt_template.format(
        date=today_display,
        market_data=market_data_str,
        bullish_signal=bullish_signal,
        ai_topic=ai_topic
    )

    with open(OUTPUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(script_text)
    print(f"✅ 已產出逐字稿：{OUTPUT_SCRIPT}")


if __name__ == "__main__":
    main()