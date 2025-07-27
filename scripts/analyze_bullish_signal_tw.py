# scripts/analyze_bullish_signal_tw.py

from datetime import datetime
from utils_tw_data import get_latest_taiex_summary
import os

def analyze_bullish_signal_tw():
    today = datetime.now().strftime("%Y%m%d")
    print(f"📊 分析日期：{today}")

    df = get_latest_taiex_summary()
    if df is None or df.empty:
        print("❌ 無法取得大盤資料")
        return

    row = df.iloc[-1]
    print("🔍 row data:", row.to_dict())

    try:
        close = float(row.get("close"))
        ma5 = float(row.get("ma5"))
        ma10 = float(row.get("ma10"))
        ma20 = float(row.get("ma20"))
        ma60 = float(row.get("ma60"))
    except Exception as e:
        print(f"⚠️ 無法轉換為數字格式：{e}")
        close = ma5 = ma10 = ma20 = ma60 = None

    # 判斷訊號
    if all(isinstance(v, float) for v in [close, ma5, ma10, ma20, ma60]):
        if close > ma5 > ma10 > ma20 > ma60:
            signal = "📈 加權指數呈現多頭排列，市場偏多。"
        else:
            signal = "📉 加權指數尚未形成多頭排列，需觀察。"
    else:
        signal = "⚠️ 均線資料不完整，無法判斷多空。"

    output = [
        f"📊 分析日期：{row['date'].strftime('%Y%m%d')}",
        f"收盤：{close:.2f}" if isinstance(close, float) else "收盤：⚠️ 無資料",
        f"5日均線：{ma5:.2f}，10日：{ma10:.2f}，月線：{ma20:.2f}，季線：{ma60:.2f}"
        if all(isinstance(v, float) for v in [ma5, ma10, ma20, ma60])
        else "⚠️ 均線資料不完整",
        signal
    ]

    output_dir = "docs/podcast"
    output_path = os.path.join(output_dir, "bullish_signal_tw.txt")
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

    print("✅ 多空判斷完成")

if __name__ == "__main__":
    analyze_bullish_signal_tw()