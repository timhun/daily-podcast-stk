# analyze_bullish_signal_tw.py
import os
from datetime import datetime
from utils_podcast import get_latest_taiex_summary, TW_TZ

def analyze_bullish_signal_taiex(row: dict) -> str:
    close = row["close"]
    ma5 = row["ma5"]
    ma10 = row["ma10"]
    ma20 = row["ma20"]
    ma60 = row["ma60"]
    macd = row.get("macd")
    volume_lots = row.get("volume_lots")
    volume_billion = row.get("volume_billion")
    date = row["date"]

    # 判斷多頭排列
    is_bullish = close > ma5 > ma10 > ma20 > ma60

    lines = []
    lines.append(f"📊 分析日期：{date.strftime('%Y%m%d')}")
    lines.append(f"收盤：{close:,.2f}")
    lines.append(f"5日均線：{ma5:,.2f}，10日：{ma10:,.2f}，月線：{ma20:,.2f}，季線：{ma60:,.2f}")
    if macd is not None:
        lines.append(f"MACD 值：{macd:.2f}")
    if volume_lots and volume_billion:
        lines.append(f"成交量：約 {volume_lots:,} 張，推估成交金額：約 {volume_billion:,} 億元")

    if is_bullish:
        lines.append("📈 加權指數呈現多頭排列，市場偏多，可以加倉 0050 或 00631L。")
    else:
        lines.append("📉 均線尚未呈現多頭排列，市場觀望或整理。")

    return "\n".join(lines)

if __name__ == "__main__":
    df = get_latest_taiex_summary()
    if df is None or df.empty:
        print("❌ 無法取得加權指數資料")
        exit(1)

    row = df.iloc[0]
    try:
        summary = analyze_bullish_signal_taiex(row)
    except Exception as e:
        print(f"⚠️ 分析失敗：{e}")
        summary = "⚠️ 均線資料不完整，無法判斷多空。"

    print(summary)

    # 儲存分析結果
    date_str = datetime.now(TW_TZ).strftime("%Y%m%d")
    output_dir = "docs/podcast"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "bullish_signal_tw.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 已儲存多空判斷至：{output_path}")
