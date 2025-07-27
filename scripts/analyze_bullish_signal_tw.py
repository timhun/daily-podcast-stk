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
    volume_billion = row.get("volume_billion")
    foreign = row.get("foreign")
    investment = row.get("investment")
    dealer = row.get("dealer")
    total_netbuy = row.get("total_netbuy")
    date = row["date"]

    is_bullish = close > ma5 > ma10 > ma20 > ma60

    lines = []
    lines.append(f"📊 分析日期：{date.strftime('%Y%m%d')}")
    lines.append(f"收盤：{close:,.2f} 點")
    lines.append(f"成交金額：約 {volume_billion:,.0f} 億元" if volume_billion else "成交金額：⚠️ 無資料")
    lines.append(f"5日均線：{ma5:,.2f}，10日：{ma10:,.2f}，月線：{ma20:,.2f}，季線：{ma60:,.2f}")
    lines.append(f"MACD 指標：{macd:.2f}" if macd is not None else "MACD 指標：⚠️ 無資料")

    if is_bullish:
        lines.append("📈 均線呈現多頭排列，市場趨勢偏多!可以加倉0050~")
    else:
        lines.append("📉 均線尚未形成多頭排列，建議觀望或減碼。")

    if total_netbuy is not None:
        lines.append("📥 法人買賣超（億元）：")
        lines.append(f"　外資：{foreign:>+,.1f}，投信：{investment:>+,.1f}，自營商：{dealer:>+,.1f}")
        lines.append(f"　➡️ 合計：{total_netbuy:>+,.1f} 億元")
    else:
        lines.append("📥 法人買賣超資料：⚠️ 無法取得")

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
        summary = "⚠️ 均線或法人資料不完整，無法判斷多空。"

    print(summary)

    # 儲存結果
    date_str = datetime.now(TW_TZ).strftime("%Y%m%d")
    output_path = "docs/podcast/bullish_signal_tw.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 已儲存多空判斷至：{output_path}")
