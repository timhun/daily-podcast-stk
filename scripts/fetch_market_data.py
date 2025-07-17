import os
import json

# 自動建立目錄
os.makedirs('podcast/latest', exist_ok=True)

data = {
    ".DJI": {"close": 40000, "change": 0.25},
    ".IXIC": {"close": 18000, "change": 0.4},
    ".SPX": {"close": 5500, "change": 0.12},
    "SOX": {"close": 5300, "change": 0.7},
    "QQQ": {"close": 480, "change": 0.32},
    "SPY": {"close": 560, "change": 0.15},
    "IBIT": {"close": 35, "change": 0.8},
    "BTC": {"close": 65000, "change": 1.3},
    "Gold": {"close": 2400, "change": -0.15},
    "US10Y": {"close": 4.2, "change": 0.01},
    "Top5": ['AAPL', 'TSLA', 'NVDA', 'AMZN', 'META']
}

with open('podcast/latest/market.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)

print("✅ [MOCK] Market data 已產生")