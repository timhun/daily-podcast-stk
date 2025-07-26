# analyze_bullish_signal_tw.py
import os
import pandas as pd
from datetime import datetime, timedelta
from utils_tw_data import get_price_volume_tw, get_trading_days  # ✅ 匯入 get_trading_days

def calculate_ma(prices, window):
    return prices.rolling(window=window).mean()

def composite_index_with_volume_and_bullish(prices, volume, weights=[0.4, 0.35, 0.25]):
    ma_5 = calculate_ma(prices, 5)
    ma_10 = calculate_ma(prices, 10)
    ma_60 = calculate_ma(prices, 60)

    bullish = (ma_5 > ma_10) & (ma_10 > ma_60)

    big_line = weights[0]*ma_5 + weights[1]*ma_10 + weights[2]*ma_60
    max_vol = volume.rolling(window=60).max()
    vol_factor = 1 + volume / (max_vol + 1e-9)
    big_line_weighted = big_line * vol_factor
    big_line_diff = big_line_weighted.diff()

    return pd.DataFrame({
        "MA_5": ma_5,
        "MA_10": ma_10,
        "MA_60": ma_60,
        "Bullish": bullish,
        "BigLine": big_line_weighted,
        "BigLine_Diff": big_line_diff
    })

def analyze_bullish_signal_tw():
    today = datetime.today().date()
    start_date = today - timedelta(days=90)
    # 調整 today 為最新交易日
    today = max(get_trading_days(start_date, today))
    print(f"📊 分析日期範圍：{start_date.isoformat()} 至 {today.isoformat()}")

    # 取得 TAIEX 資料
    try:
        twii_price, twii_vol = get_price_volume_tw("TAIEX", start_date=start_date, end_date=today)
        if twii_price is None or len(twii_price) < 60:
            raise RuntimeError(f"❌ 無法取得台股加權指數資料（{start_date} 至 {today}）")
    except Exception as e:
        raise RuntimeError(f"❌ TAIEX 數據獲取失敗（{start_date} 至 {today}）：{str(e)}")

    # 取得 0050 資料
    try:
        etf_price, etf_vol = get_price_volume_tw("0050", start_date=start_date, end_date=today)
        if etf_price is None or len(etf_price) < 60:
            raise RuntimeError(f"❌ 無法取得 0050 資料（{start_date} 至 {today}）")
    except Exception as e:
        raise RuntimeError(f"❌ 0050 數據獲取失敗（{start_date} 至 {today}）：{str(e)}")

    df_twii = composite_index_with_volume_and_bullish(twii_price, twii_vol)
    df_0050 = composite_index_with_volume_and_bullish(etf_price, etf_vol)

    latest_twii = df_twii.iloc[-1]
    latest_0050 = df_0050.iloc[-1]

    def line(name, df):
        bullish = "✅ 多頭排列" if df["Bullish"] else "⚠️ 非多頭"
        trend = "📈 大盤線上升" if df["BigLine_Diff"] > 0 else "📉 大盤線下滑"
        return f"{name}：{bullish}，{trend}"

    msg = [
        "【台股多空訊號判斷】",
        line("加權指數", latest_twii),
        line("0050", latest_0050)
    ]

    # 儲存結果
    output_path = "docs/podcast/bullish_signal_tw.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(msg))
    print(f"✅ 已儲存多空訊號至：{output_path}")

if __name__ == "__main__":
    analyze_bullish_signal_tw()