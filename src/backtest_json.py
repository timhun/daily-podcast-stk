# src/backtest_json.py
import pandas as pd
import json

def run_daily_sim_json(df, strategy_data, mode="daily"):
    """
    根據策略回測
    :param df: pd.DataFrame - 必須包含 OHLC 資料
    :param strategy_data: dict - 策略條件
    :param mode: "daily" 或 "hourly"
    :return: dict - 回測結果
    """
    if df is None or df.empty:
        return {"error": "DataFrame is empty"}

    if mode not in ["daily", "hourly"]:
        raise ValueError("mode 必須是 daily 或 hourly")

    # 將時間欄位標準化
    if "Datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["Datetime"])
    elif "Date" in df.columns:
        df["datetime"] = pd.to_datetime(df["Date"])
    else:
        raise ValueError("DataFrame 缺少時間欄位")

    df = df.sort_values("datetime").reset_index(drop=True)

    # 簡單的策略模擬範例（真實可改成你的邏輯）
    capital = 1000000
    position = 0
    trades = []

    for i in range(1, len(df)):
        # 模擬條件（這裡簡化）
        price_today = df.loc[i, "Close"]
        price_yesterday = df.loc[i - 1, "Close"]

        # 假設策略：價格突破昨日收盤 -> 買進
        if price_today > price_yesterday and position == 0:
            position = capital / price_today
            capital = 0
            trades.append({"action": "buy", "price": price_today, "time": df.loc[i, "datetime"]})

        # 價格跌破昨日收盤 -> 賣出
        elif price_today < price_yesterday and position > 0:
            capital = position * price_today
            position = 0
            trades.append({"action": "sell", "price": price_today, "time": df.loc[i, "datetime"]})

    final_value = capital + position * df.loc[len(df) - 1, "Close"]

    return {
        "mode": mode,
        "final_value": final_value,
        "trades": trades,
        "profit_pct": (final_value - 1000000) / 1000000
    }
