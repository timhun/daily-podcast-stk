import os
import pandas as pd
from datetime import datetime
from utils_tw_data import get_latest_taiex_summary

OUTPUT_FILE = "docs/podcast/bullish_signal_tw.txt"

def analyze_bullish_signal(df: pd.DataFrame) -> str:
    """
    根據加權指數資料進行基本的多空分析。
    預期 df 包含 date, close, change, change_pct 欄位。
    """
    close = df["close"].iloc[0]
    change = df["change"].iloc[0]
    change_pct = df["change_pct"].iloc[0]

    # 模擬條件：當日漲幅 > 0 且未來可擴充均線排列
    if change > 0 and change_pct >= 0.3:
        signal = "📈 今日台股上漲超過 0.3%，短線動能偏多，觀察可望續強。"
    elif change > 0:
        signal = "🔹 台股今日小幅上漲，盤勢維持穩健，但尚未明顯轉強。"
    elif change < 0 and abs(change_pct) >= 0.3:
        signal = "📉 台股今日下跌超過 0.3%，短線修正壓力浮現，需留意支撐。"
    else:
        signal = "🔸 台股今日變動有限，短線觀望氣氛濃厚。"

    return f"【台股多空判斷】\n{signal}\n（加權指數收盤：{close:.0f} 點，漲跌：{change:+.2f} 點 / {change_pct:+.2f}%）"

def main():
    df = get_latest_taiex_summary()
    if df is None or df.empty:
        result = "❌ 無法取得今日加權指數資料，請稍後再試。"
    else:
        result = analyze_bullish_signal(df)

    # 儲存分析結果
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print("✅ 台股多空分析完成，已輸出至", OUTPUT_FILE)
    print(result)

if __name__ == "__main__":
    main()