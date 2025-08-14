# src/daily_sim.py
import pandas as pd
from datetime import datetime

def run_daily_sim(symbol, strategy_path=None, strategy_data=None, cash=1_000_000):
    """
    strategy_data: JSON dict from LLM
    """
    # 模擬抓取當日價格（這裡用假資料，可改成實際 API）
    today_price = 100  # 假設價格
    df = pd.DataFrame({"close":[today_price]})

    # 使用 strategy_data 計算 signal
    signal_info = strategy_data.get("generate_signal", lambda df: {"signal":"hold"})(df)
    signal = signal_info.get("signal", "hold")
    size_pct = signal_info.get("size_pct", 0.5)
    position_size = cash * size_pct if signal == "buy" else 0

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "symbol": symbol,
        "signal": signal,
        "price": today_price,
        "size": position_size,
        "strategy_name": strategy_data.get("name", "LLM Strategy"),
        "summary": strategy_data.get("summary", "")
    }
