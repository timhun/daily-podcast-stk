def get_stock_index_data_us():
    # 這是原本的美股資料擷取邏輯
    return [
        "🔹 S&P 500 上漲 1.2%",
        "🔸 Nasdaq 下跌 0.6%",
        "🔺 Dow Jones 持平"
    ]

def get_stock_index_data_tw():
    return [
        "📈 加權指數上漲 0.85%，收在 17600 點",
        "📉 櫃買指數下跌 0.3%，AI 概念股震盪整理",
        "🏦 電金族群穩健支撐台股"
    ]

def get_etf_data_us():
    return [
        "📊 QQQ 上漲 1.1%，科技股回溫",
        "📊 SPY 上漲 0.5%，金融與能源支撐走勢",
        "📊 IBIT 微幅震盪"
    ]

def get_etf_data_tw():
    return [
        "📊 台灣 0050 上漲 0.7%，AI、半導體領漲",
        "📊 00878 持續吸引高股息族群",
        "📊 00929 短期波動加劇"
    ]

# 其他共用資料
def get_bitcoin_price(): return "₿ 比特幣現價 $63,500"
def get_gold_price(): return "🪙 黃金每盎司 $2,390"
def get_dxy_index(): return "💵 美元指數 DXY 為 103.5"
def get_yield_10y(): return "📉 美國 10Y 殖利率為 4.10%"

def get_market_data_by_mode(mode: str) -> str:
    if mode == "tw":
        stock_summary = "\n".join(get_stock_index_data_tw())
        etf_summary = "\n".join(get_etf_data_tw())
    else:
        stock_summary = "\n".join(get_stock_index_data_us())
        etf_summary = "\n".join(get_etf_data_us())

    return f"""
【股市概況】
{stock_summary}

【ETF 概況】
{etf_summary}

【其他市場指標】
{get_bitcoin_price()}
{get_gold_price()}
{get_yield_10y()}
{get_dxy_index()}
""".strip()
