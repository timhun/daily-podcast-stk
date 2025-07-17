import os
import json

os.makedirs('podcast/latest', exist_ok=True)

# 防呆 mock
if not os.path.exists('podcast/latest/market.json'):
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

with open('podcast/latest/market.json') as f:
    market = json.load(f)
with open('podcast/latest/news_ai.txt') as f:
    news_ai = f.read()
with open('podcast/latest/news_macro.txt') as f:
    news_macro = f.read()
with open('podcast/latest/quote.txt') as f:
    quote = f.read()

# mock 逐字稿內容
script = f"""
【幫幫忙說財經科技投資】Podcast 範例逐字稿
美股四大指數收盤分別為：.DJI {market['.DJI']['close']}、.IXIC {market['.IXIC']['close']}、.SPX {market['.SPX']['close']}、SOX {market['SOX']['close']}。漲跌幅依序：{market['.DJI']['change']}%、{market['.IXIC']['change']}%、{market['.SPX']['change']}%、{market['SOX']['change']}%。

ETF方面，QQQ為{market['QQQ']['close']}點，SPY為{market['SPY']['close']}點，IBIT為{market['IBIT']['close']}美元。比特幣目前報價{market['BTC']['close']}美元，黃金每盎司{market['Gold']['close']}美元，十年美債殖利率{market['US10Y']['close']}%。

今日熱門五檔美股為：{'、'.join(market['Top5'])}。

AI新聞：{news_ai}
總經新聞：{news_macro}
投資金句：{quote}
"""

with open('podcast/latest/script.txt', 'w') as f:
    f.write(script)

print("✅ [MOCK] Podcast 逐字稿已產生")