import json

INPUT = "docs/podcast/market_data_tw.json"
OUTPUT = "docs/podcast/bullish_signal_tw.txt"

def analyze_signal():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        close = float(data["taiex_close"])
        ma5 = float(data["ma5"])
        ma10 = float(data["ma10"])
        ma20 = float(data["ma20"])
        macd = float(data["macd"])
        macd_signal = float(data["macd_signal"])
        bullish = ""

        if close > ma5 > ma10 > ma20:
            bullish = "📈 均線呈現多頭排列，市場偏多。"
        elif macd > macd_signal:
            bullish = "📈 MACD 處於正向交叉，動能偏多。"
        else:
            bullish = "📉 尚未出現明確多頭訊號，建議觀望。"

        lines = [
            f"📊 分析日期：{data['date']}",
            f"收盤：{close:.2f} 點，成交金額 {data['volume']} 億元",
            f"外資：{data['foreign_buy']} 億，投信：{data['investment_buy']} 億，自營商：{data['dealer_buy']} 億",
            f"MA5: {ma5:.2f}，MA10: {ma10:.2f}，MA20: {ma20:.2f}",
            f"MACD: {macd:.2f}，Signal: {macd_signal:.2f}",
            bullish
        ]

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("✅ 多空判斷完成")
    except Exception as e:
        print("❌ 多空分析失敗：", e)

if __name__ == "__main__":
    analyze_signal()
