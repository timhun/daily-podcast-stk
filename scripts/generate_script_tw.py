import os
import json
from datetime import datetime
import pytz

from utils_podcast_tw import (
    get_today_tw_ymd_str,
    is_weekend_tw,
    is_tw_holiday,
    load_prompt_template
)
from grok_api import ask_grok  # ✅ 導入 Grok API 呼叫函式

# 今日資訊
TODAY = get_today_tw_ymd_str()
MODE = "tw"
BASE_DIR = f"docs/podcast/{TODAY}_{MODE}"
os.makedirs(BASE_DIR, exist_ok=True)

# 檔案路徑
MARKET_DATA_FILE = f"{BASE_DIR}/market_data_tw.json"
SIGNAL_FILE = f"{BASE_DIR}/bullish_signal_tw.txt"
AI_TOPIC_FILE = "ai_topic.txt"
OUTPUT_SCRIPT = f"{BASE_DIR}/script.txt"

def load_text_file(filepath: str) -> str:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def select_prompt_file() -> str:
    if is_tw_holiday():
        print("📅 今天是台灣國定假日，使用 tw_holiday.txt 模板")
        return "prompt/tw_holiday.txt"
    elif is_weekend_tw():
        print("📅 今天是週末，使用 tw_weekend.txt 模板")
        return "prompt/tw_weekend.txt"
    else:
        print("📅 今天為平日交易日，使用 tw.txt 模板")
        return "prompt/tw.txt"

def main():
    # 載入 prompt 與資料
    prompt_file = select_prompt_file()
    prompt_template = load_prompt_template(prompt_file)

    try:
        with open(MARKET_DATA_FILE, "r", encoding="utf-8") as f:
            market_data = json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"❌ 找不到 JSON 資料：{MARKET_DATA_FILE}") from e

    bullish_signal = load_text_file(SIGNAL_FILE)
    ai_topic = load_text_file(AI_TOPIC_FILE)

    # 格式化 prompt
    today_display = datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y年%m月%d日")
    market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)

    full_prompt = prompt_template.format(
        date=today_display,
        market_data=market_data_str,
        bullish_signal=bullish_signal,
        ai_topic=ai_topic,
    )

    print("📨 傳送合成後 prompt 給 Grok...")
    script_text = ask_grok(full_prompt)

    with open(OUTPUT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(script_text)

    print(f"✅ 已產出逐字稿：{OUTPUT_SCRIPT}")


if __name__ == "__main__":
    main()