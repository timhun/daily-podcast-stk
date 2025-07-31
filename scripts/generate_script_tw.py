#generate_script_tw.py
import json
from datetime import datetime
import pytz

from grok_api import ask_grok

def load_template(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    # 設置台灣時區
    TW_TZ = pytz.timezone("Asia/Taipei")
    TODAY = datetime.now(TW_TZ)
    today_display = TODAY.strftime("%Y-%m-%d")
    today_str = TODAY.strftime("%Y%m%d")

    # 讀取市場數據
    market_data_file = f"docs/podcast/{today_str}_tw/market_data_tw.json"
    try:
        with open(market_data_file, "r", encoding="utf-8") as f:
            market_data = json.load(f)
        market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)
    except FileNotFoundError:
        print(f"❌ 找不到市場數據檔案：{market_data_file}")
        # 使用回退數據
        market_data = {
            "date": today_display,
            "taiex": {"close": 23201.52, "change_percent": -0.9},
            "volume": 3500,
            "institutions": {"foreign": 50.0, "investment": -10.0, "dealer": 5.0},
            "moving_averages": {"ma5": 22800.0, "ma10": 22500.0}
        }
        market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)

    # 設置其他參數（假設從其他來源獲取）
    bullish_signal = "MACD金叉"  # 應從實際來源獲取
    ai_topic = "台積電CPO技術進展"  # 應從實際來源獲取
    theme = "台股與AI科技趨勢"  # 固定主題，解決 KeyError

    # 載入模板
    prompt_template = load_template("prompt/tw.txt")

    # 生成完整提示詞
    full_prompt = prompt_template.format(
        date=today_display,
        market_data=market_data_str,
        bullish_signal=bullish_signal,
        ai_topic=ai_topic,
        theme=theme
    )

    # 調用 Grok 生成逐字稿
    try:
        script = ask_grok(full_prompt)
        print("📜 生成逐字稿：\n", script)
        # 保存逐字稿（可根據需求調整）
        output_dir = f"docs/podcast/{today_str}__tw"
        os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}/script_tw.txt", "w", encoding="utf-8") as f:
            f.write(script)
        print(f"✅ 已儲存逐字稿至 {output_dir}/script_tw.txt")
    except Exception as e:
        print(f"❌ 生成逐字稿失敗：{e}")

if __name__ == "__main__":
    main()
