# scripts/analyze_bullish_signal_from_prompt.py
import json

def analyze_bullish_signal():
    with open("market_data_tw.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        close = float(data["taiex_close"])
        ma5 = float(data["ma5"])
        ma10 = float(data["ma10"])
        ma20 = float(data["ma20"])
        macd = float(data["macd"])
    except Exception as e:
        print("⚠️ 資料錯誤，無法分析：", e)
        return

    result = [f"📊 分析日期：{data['date']}"]
    result.append(f"收盤：{close:.2f}，5日均：{ma5:.2f}，10日：{ma10:.2f}，20日：{ma20:.2f}，MACD：{macd:.2f}")

    if close > ma5 > ma10 > ma20:
        signal = "📈 多頭排列，市場偏多。"
    elif macd > 0:
        signal = "📈 MACD 為正，短期偏多。"
    else:
        signal = "📉 尚未出現明顯多頭訊號，市場觀望。"

    result.append(signal)

    with open("bullish_signal_tw.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(result))

    print("✅ 產出 bullish_signal_tw.txt")

if __name__ == "__main__":
    analyze_bullish_signal()