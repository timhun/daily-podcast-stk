# analyze_bullish_signal_tw.pyimport os
from datetime import datetime
from utils_tw_data import get_latest_taiex_summary

def analyze_bullish_signal_tw():
    print(f"📊 分析日期：{datetime.now().strftime('%Y%m%d')}")

    df = get_latest_taiex_summary()
    if df is None or df.empty:
        print("❌ 無法取得加權指數資料")
        return

    row = df.iloc[0]
    close = row["close"]
    ma5 = row.get("ma5")
    ma10 = row.get("ma10")
    ma20 = row.get("ma20")
    ma60 = row.get("ma60")

    signal = "❓ 無法判斷"
    if all(v is not None for v in [close, ma5, ma10, ma20, ma60]):
        if close > ma5 > ma10 > ma20 > ma60:
            signal = "🔼 出現多頭排列，市場偏多"
        elif close < ma5 < ma10 < ma20 < ma60:
            signal = "🔽 出現空頭排列，市場偏空"
        else:
            signal = "🔁 均線糾結，等待方向"

    output_lines = [
        f"📈 加權指數收盤：{close:.2f} 點",
        f"5日均線：{ma5:.2f}，10日：{ma10:.2f}，月線：{ma20:.2f}，季線：{ma60:.2f}",
        f"📌 判斷結果：{signal}"
    ]

    output_text = "\n".join(output_lines)

    # 儲存到 docs/podcast/bullish_signal_tw.txt
    os.makedirs("../docs/podcast", exist_ok=True)
    with open("../docs/podcast/bullish_signal_tw.txt", "w", encoding="utf-8") as f:
        f.write(output_text)

    print("✅ 多空判斷完成，已儲存 bullish_signal_tw.txt")

if __name__ == "__main__":
    analyze_bullish_signal_tw()
