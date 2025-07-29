import json
import os
from datetime import datetime
import pytz

TW_TZ = pytz.timezone("Asia/Taipei")
TODAY = datetime.now(TW_TZ).strftime("%Y%m%d")

INPUT_JSON = f"docs/podcast/{TODAY}_tw/market_data_tw.json"
OUTPUT_TXT = f"docs/podcast/{TODAY}_tw/bullish_signal_tw.txt"


def analyze_bullish_signal(data: dict) -> str:
    lines = []

    # 均線判斷
    try:
        ma5 = float(data["ma5"])
        ma10 = float(data["ma10"])
        ma20 = float(data["ma20"])
        index = float(data["close"])
        if index > ma5 > ma10 > ma20:
            lines.append("📈 加權指數呈現多頭排列，短期趨勢偏多。")
        elif index < ma5 < ma10 < ma20:
            lines.append("📉 加權指數呈現空頭排列，市場走勢偏弱。")
        else:
            lines.append("📊 均線尚未明確排列，短期走勢呈現震盪整理。")
    except Exception:
        lines.append("⚠️ 無法判斷均線排列，多空訊號不足。")

    # MACD 判斷
    try:
        macd = float(data["macd"])
        if macd > 0:
            lines.append("✅ MACD 為正，動能偏多。")
        else:
            lines.append("🚨 MACD 為負，動能轉弱。")
    except Exception:
        lines.append("⚠️ MACD 資料缺失。")

    # 法人買賣超
    try:
        total_netbuy = int(data["total_netbuy"])
        if total_netbuy > 0:
            lines.append(f"💰 三大法人合計買超 {total_netbuy} 張，偏多看待。")
        elif total_netbuy < 0:
            lines.append(f"💸 三大法人合計賣超 {abs(total_netbuy)} 張，籌碼偏空。")
        else:
            lines.append("📎 三大法人買賣超持平，觀望氣氛濃厚。")
    except Exception:
        lines.append("⚠️ 法人買賣超資料不足。")

    return "\n".join(lines)


if __name__ == "__main__":
    if not os.path.exists(INPUT_JSON):
        raise FileNotFoundError(f"❌ 找不到 JSON 資料：{INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = analyze_bullish_signal(data)

    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"✅ 已輸出多空分析至 {OUTPUT_TXT}")