# analyze_bullish_signal_tw.py

import os
import pandas as pd
from datetime import datetime, timedelta
from utils_tw_data import get_latest_taiex_summary, get_price_volume_tw

OUTPUT_FILE = "docs/podcast/bullish_signal_tw.txt"

def analyze_bullish_signal(data: dict) -> str:
    """
    根據最新資料進行台股多空判斷
    """
    close = data.get("close")
    volume = data.get("volume")
    ma5 = data.get("5MA")
    ma10 = data.get("10MA")
    monthly = data.get("monthly")
    quarterly = data.get("quarterly")
    change = data.get("change")
    change_pct = data.get("change_pct")
    date = data.get("date")

    if not all([close, volume, change, change_pct]):
        return "❌ 資料不完整，無法進行判斷。"

    # 多空條件簡單範例
    if change > 0 and change_pct >= 0.3:
        signal = "📈 今日台股上漲超過 0.3%，短線動能偏多，觀察可望續強。"
    elif change > 0:
        signal = "🔹 台股今日小幅上漲，盤勢維持穩健，但尚未明顯轉強。"
    elif change < 0 and abs(change_pct) >= 0.3:
        signal = "📉 台股今日下跌超過 0.3%，短線修正壓力浮現，需留意支撐。"
    else:
        signal = "🔸 台股今日變動有限，短線觀望氣氛濃厚。"

    ma_str = f"（5MA：{ma5:.0f}, 10MA：{ma10:.0f}, 月線：{monthly:.0f}, 季線：{quarterly:.0f}）" \
        if all([ma5, ma10, monthly, quarterly]) else ""

    return (
        f"【台股多空判斷】\n{signal}\n"
        f"（{date} 收盤：{close:.0f} 點，漲跌：{change:+.2f} 點 / {change_pct:+.2f}%）\n"
        f"{ma_str}"
    )

def main():
    try:
        # 取得最新收盤資料與均線
        latest = get_latest_taiex_summary()

        # 補抓昨日收盤來算漲跌
        today = datetime.strptime(latest["date"], "%Y-%m-%d").date()
        yesterday = today - timedelta(days=5)  # 假設歷史資料 fallback 可排除假日
        prices, _ = get_price_volume_tw("TAIEX", start_date=yesterday, end_date=today)
        prices = prices.sort_index()
        if len(prices) >= 2:
            yesterday_close = prices.iloc[-2]
            today_close = prices.iloc[-1]
            latest["change"] = today_close - yesterday_close
            latest["change_pct"] = (today_close - yesterday_close) / yesterday_close * 100
        else:
            raise RuntimeError("❌ 無法取得昨日收盤價")
    except Exception as e:
        print(f"❌ 資料取得失敗：{e}")
        result = "❌ 無法取得今日加權指數資料，請稍後再試。"
    else:
        result = analyze_bullish_signal(latest)

    # 輸出結果
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print("✅ 台股多空分析完成，已輸出至", OUTPUT_FILE)
    print(result)

if __name__ == "__main__":
    main()