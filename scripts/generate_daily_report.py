#!/usr/bin/env python3
# scripts/generate_daily_report.py
import datetime, yfinance as yf, pandas as pd, numpy as np

TICKERS = ["QQQ", "0050.TW"]
START = datetime.datetime.now() - datetime.timedelta(days=730)
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")
REPORT = "# 每日策略報告 — " + TODAY + "\n\n"

for t in TICKERS:
    df = yf.download(t, start=START.strftime("%Y-%m-%d"), end=(datetime.datetime.now()+datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    df.dropna(inplace=True)
    df["MA5"], df["MA20"] = df["Close"].rolling(5).mean(), df["Close"].rolling(20).mean()
    df.dropna(inplace=True)
    df["Signal"] = np.where(df["MA5"] > df["MA20"], "BUY", "SELL")
    win_rate = (df["Signal"].shift(1) == df["Signal"]).mean() * 100  # 替代勝率計算
    REPORT += f"## {t}\n- Signal: {df['Signal'].iloc[-1]}\n- WinRate: {win_rate:.2f}%\n\n"

with open("daily_report.md", "w", encoding="utf-8") as f:
    f.write(REPORT)


if __name__ == "__main__":
    main()
