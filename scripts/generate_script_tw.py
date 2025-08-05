#generate_script_tw.py
import json
import os
from datetime import datetime
import pytz
import logging

from grok_api import ask_grok

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_template(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def get_fallback_transcript(market_data: dict, today_display: str) -> str:
    """生成回退逐字稿"""
    return f"""
大家好，我是幫幫忙，歡迎收聽《幫幫忙說台股》！今天是{today_display}，由於技術問題，無法獲取最新市場分析，以下為簡訊播報。

1. **台股概況**：加權指數收盤 {market_data['taiex']['close']} 點，漲跌幅 {market_data['taiex']['change_percent']}%，成交量 {market_data['volume']} 億元。支撐位約 {market_data['moving_averages']['ma5']-200:.2f} 點，壓力位約 {market_data['moving_averages']['ma5']+200:.2f} 點。
2. **0050 ETF**：收盤價約 85.00 元，支撐位 83.00 元，壓力位 88.00 元。
3. **交易策略**：短線偏多，建議逢低布局，止損設在 82.00 元。
4. **三大法人**：外資買超 {market_data['institutions']['foreign']} 億元，投信賣超 {market_data['institutions']['investment']} 億元，自營商買超 {market_data['institutions']['dealer']} 億元。
5. **期貨動向**：外資期貨淨多單約 2 萬口。
6. **AI 新聞**：台積電持續推進 CPO 技術，預計 2026 年放量，利好 AI 供應鏈。
7. **投資金句**：穩中求進，台股未來在你手中！

感謝收聽，我們明天見！
"""

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
        logger.error(f"找不到市場數據檔案：{market_data_file}")
        market_data = {
            "date": today_display,
            "taiex": {"close": 23201.52, "change_percent": -0.9},
            "volume": 3500,
            "institutions": {"foreign": 50.0, "investment": -10.0, "dealer": 5.0},
            "moving_averages": {"ma5": 22800.0, "ma10": 22500.0}
        }
        market_data_str = json.dumps(market_data, ensure_ascii=False, indent=2)

    # 設置參數
    bullish_signal = "MACD金叉"  # 應從實際來源獲取
    ai_topic = "台積電CPO技術進展"  # 應從實際來源獲取
    theme = "台股與AI科技趨勢"

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
    output_dir = f"docs/podcast/{today_str}_tw"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/script_tw.txt"
    try:
        script = ask_grok(full_prompt)
        logger.info("成功生成逐字稿")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(script)
        logger.info(f"已儲存逐字稿至 {output_file}")
    except Exception as e:
        logger.error(f"生成逐字稿失敗：{e}")
        # 使用回退逐字稿
        script = get_fallback_transcript(market_data, today_display)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(script)
        logger.info(f"已儲存回退逐字稿至 {output_file}")

if __name__ == "__main__":
    main()
