# src/daily_sim.py
import pandas as pd
import numpy as np

def run_daily_sim(symbol, strategy_data, cash=1_000_000):
    """
    模擬每日交易，回傳 signal/price/size
    """
    # 模擬今日價格變動
    price = np.random.uniform(95, 105)  # 隨機示意
    signal = "hold"
    size = 0

    if strategy_data["regime"] == "trend":
        if np.random.rand() > 0.5:
            signal = "buy"
            size = strategy_data["params"]["size_pct"]
        else:
            signal = "sell"
            size = strategy_data["params"]["size_pct"]
    else:
        if np.random.rand() > 0.5:
            signal = "buy"
            size = strategy_data["params"]["size_pct"]
        else:
            signal = "sell"
            size = strategy_data["params"]["size_pct"]

    return {"signal": signal, "price": round(price,2), "size": size}
