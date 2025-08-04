import os
import yfinance as yf
from utils_podcast import get_latest_taiex_summary

def get_stock_index_data_tw():
    """
    擷取台灣時間今天台股加權指數資訊，回傳格式化後文字
    """
    df = get_latest_taiex_summary()
    if df is not None and not df.empty:
        row = df.iloc[0]
        index = float(row["close"])
        change = float(row["change"])
        percent = float(row["change_pct"])
        volume_billion = row.get("volume_billion", None)
        lines = [f"台股加權指數：{index:.2f}（{change:+.2f}, {percent:+.2f}%）"]
        if volume_billion:
            lines.append(f"成交金額：約 {volume_billion:.0f} 億元")

        return lines
    else:
        return ["⚠️ 無法取得台股指數資料"]

def get_stock_index_data_us():
    """
    擷取台灣時間今天上午五點美國主要指數的實際收盤數據（道瓊、標普500、那斯達克）
    """
    try:
        # 定義美國主要指數的代碼
        indices = {
            "道瓊指數": "^DJI",
            "標普500指數": "^GSPC", 
            "那斯達克指數": "^IXIC", 
            "QQQ": "QQQ", 
            "SPY": "SPY", 
            "IBIT": "IBIT"
        }
        
        lines = []
        for name, ticker in indices.items():
            # 使用 yfinance 獲取最新數據
            index_data = yf.Ticker(ticker).history(period="1d")
            if not index_data.empty:
                row = index_data.iloc[-1]
                close = float(row["Close"])
                change = float(row["Close"] - row["Open"])
                percent = (change / row["Open"]) * 100
                lines.append(f"美股{name}：{close:,.2f}（{change:+.2f}, {percent:+.2f}%）")
            else:
                lines.append(f"⚠️ 無法取得美股{name}資料")
        
        return lines
    except Exception as e:
        return ["⚠️ 無法取得美股指數資料，請檢查網路連線或數據源"]

def get_market_summary(mode: str = "tw") -> str:
    """
    回傳整段 market_data 給 prompt 注入使用
    """
    if mode == "tw":
        return "\n".join(get_stock_index_data_tw())
    elif mode == "us":
        return "\n".join(get_stock_index_data_us())
    else:
        return "\n".join(get_stock_index_data_tw() + get_stock_index_data_us())
