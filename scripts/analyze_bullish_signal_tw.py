# analyze_bullish_signal_tw.py

import logging
from utils_tw_data import get_latest_taiex_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def analyze_bullish_signal_tw():
    try:
        summary = get_latest_taiex_summary()
        latest_close = summary['close']
        ma5 = summary['ma5']
        ma10 = summary['ma10']
        ma20 = summary['ma20']
        ma60 = summary['ma60']
        date = summary['date']

        signals = []
        if latest_close > ma5:
            signals.append("短線偏多（收盤 > 5日均線）")
        else:
            signals.append("短線偏空（收盤 < 5日均線）")

        if latest_close > ma10:
            signals.append("中線偏多（收盤 > 10日均線）")
        else:
            signals.append("中線偏空（收盤 < 10日均線）")

        if latest_close > ma20:
            signals.append("月線偏多（收盤 > 月線）")
        else:
            signals.append("月線偏空（收盤 < 月線）")

        if latest_close > ma60:
            signals.append("季線偏多（收盤 > 季線）")
        else:
            signals.append("季線偏空（收盤 < 季線）")

        summary_text = f"""📈 台股技術線判斷（{date} 收盤）：
- 收盤指數：{latest_close:,.0f} 點
- 5 日均線：{ma5:,.0f}
- 10 日均線：{ma10:,.0f}
- 月線（20 日）：{ma20:,.0f}
- 季線（60 日）：{ma60:,.0f}

多空觀察：
{chr(10).join(f"- {s}" for s in signals)}
"""
        # 輸出至文字檔
        with open("bullish_signal_tw.txt", "w", encoding="utf-8") as f:
            f.write(summary_text)

        logging.info("✅ 分析完成，已輸出 bullish_signal_tw.txt")
        print(summary_text)

    except Exception as e:
        logging.error(f"❌ 多空判斷失敗：{e}")

if __name__ == "__main__":
    analyze_bullish_signal_tw()