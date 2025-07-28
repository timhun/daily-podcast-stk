import os
import json
from datetime import datetime
import pytz

PROMPT_WEEKDAY = "prompt/tw.txt"
PROMPT_WEEKEND = "prompt/tw_weekend.txt"
MARKET_DATA_PATH = "market_data_tw.json"
BULLISH_SIGNAL_PATH = "docs/podcast/bullish_signal_tw.txt"
AI_TOPIC_PATH = "ai_topic.txt"

TW_TZ = pytz.timezone("Asia/Taipei")

def is_weekend():
    now = datetime.now(TW_TZ)
    return now.weekday() in (5, 6)  # Sat=5, Sun=6

def load_text_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到 JSON 檔案：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    now = datetime.now(TW_TZ)
    today_str = now.strftime("%Y%m%d")
    today_display = now.strftime("%Y年%m月%d日")

    # 載入 prompt
    prompt_path = PROMPT_WEEKEND if is_weekend() else PROMPT_WEEKDAY
    prompt_template = load_text_file(prompt_path)

    # 載入 market_data
    market_data = load_json(MARKET_DATA_PATH)
    market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)

    # 載入 bullish_signal
    bullish_signal = load_text_file(BULLISH_SIGNAL_PATH)

    # 載入 AI topic
    ai_topic = load_text_file(AI_TOPIC_PATH)

    # 替換 prompt 中的佔位符
    script = prompt_template.format(
        date=today_display,
        market_data=market_data_str,
        bullish_signal=bullish_signal,
        ai_topic=ai_topic
    )

    # 儲存逐字稿
    output_dir = f"docs/podcast/{today_str}_tw"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "script.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    print(f"✅ 已產生逐字稿：{output_path}")

if __name__ == "__main__":
    main()
