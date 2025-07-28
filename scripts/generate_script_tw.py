# scripts/generate_script_tw.py
import os
import json
import datetime
import pytz
from utils_podcast import load_prompt_template, is_weekend_tw

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_txt(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def generate_script():
    today = datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%Y%m%d")
    prompt_path = "prompt/tw_weekend.txt" if is_weekend_tw() else "prompt/tw.txt"
    prompt = load_prompt_template(prompt_path)

    market_data = load_json("market_data_tw.json")
    bullish_signal = load_txt("bullish_signal_tw.txt")
    ai_topic = load_txt("ai_topic.txt")

    # 注入
    prompt_filled = prompt.format(
        date=market_data.get("date", today),
        market_data=json.dumps(market_data, ensure_ascii=False, indent=2),
        bullish_signal=bullish_signal,
        ai_topic=ai_topic,
    )

    # 儲存
    output_dir = f"docs/podcast/{today}_tw"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/script.txt", "w", encoding="utf-8") as f:
        f.write(prompt_filled)

    print("✅ 完成：產出 script.txt")

if __name__ == "__main__":
    generate_script()