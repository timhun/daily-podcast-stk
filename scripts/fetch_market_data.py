#fetch_market_data.py
import os
from utils_podcast import get_latest_taiex_summary

def get_stock_index_data_tw():
    """
    擷取台股加權指數資訊，回傳格式化後文字
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
    擷取美股主要指數資訊（模擬，可依實際情況擴充）
    """
    return [
        "美股道瓊指數：38,000（+200, +0.53%）",
        "標普500指數：5,000（+30, +0.60%）",
        "那斯達克指數：16,000（+150, +0.95%）"
    ]


def get_market_summary(mode: str = "tw") -> str:
    """
    回傳整段 market_data 給 prompt 注入使用
    """
    if mode == "tw":
        sections = get_stock_index_data_tw()
    else:
        sections = get_stock_index_data_us()

    return "\n".join(sections)


# CLI 測試
if __name__ == "__main__":
    mode = os.getenv("PODCAST_MODE", "tw")
    print(get_market_summary(mode))

