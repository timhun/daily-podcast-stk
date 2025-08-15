# src/backtest_json.py
import pandas as pd
import json
from datetime import datetime, timedelta

def run_daily_sim_json(data_file, strategy, mode="daily"):
    """
    回測策略（支援日線、週線、小時線）
    Args:
        data_file (str): JSON / CSV 檔案路徑
        strategy (dict): 策略
        mode (str): "daily"、"weekly"、"hourly"
    Returns:
        dict: 回測結果
    """
    if data_file.endswith(".csv"):
        df = pd.read_csv(data_file)
    else:
        with open(data_file, "r") as f:
            df = pd.DataFrame(json.load(f))

    # 轉時間格式
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    elif "date" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"])

    # 模式過濾
    if mode == "weekly":
        df = df.resample("W", on="datetime").last()
    elif mode == "hourly":
        # 假設已經是小時資料
        df = df.sort_values("datetime")

    entry_price = strategy.get("entry_price")
    exit_price = strategy.get("exit_price")

    trades = []
    for _, row in df.iterrows():
        price = row["close"]
        if strategy["signal"] == "BUY" and price <= entry_price:
            trades.append((price, "entry"))
        elif strategy["signal"] == "SELL" and price >= entry_price:
            trades.append((price, "entry"))

    # 計算報酬
    if strategy["signal"] == "BUY":
        returns = (exit_price - entry_price) / entry_price
    else:
        returns = (entry_price - exit_price) / entry_price

    result = {
        "mode": mode,
        "signal": strategy["signal"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "returns": returns,
        "sharpe": returns / 0.02 if returns != 0 else 0,  # 簡化版
        "mdd": -0.05  # 假設
    }
    return result
