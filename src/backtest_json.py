#!/usr/bin/env python3
# src/backtest_json.py
import pandas as pd
import numpy as np
import datetime

def run_backtest_json(df_json_list, strategy_data, cash=1_000_000, commission=0.001):
    """
    JSON list 支援 Backtest
    df_json_list: list of dict，每筆 dict 需包含 close, open, high, low, volume
    strategy_data: dict, LLM 生成策略
    """
    df = pd.DataFrame(df_json_list)
    df = df.sort_values("date") if "date" in df.columns else df

    portfolio = cash
    positions = 0

    for idx, row in df.iterrows():
        signal = strategy_data.get("signal", "hold")
        size_pct = strategy_data.get("size_pct", 0)
        price = row["close"]

        if signal == "buy":
            positions = portfolio * size_pct / price
            portfolio -= positions * price * (1 + commission)
        elif signal == "sell":
            portfolio += positions * price * (1 - commission)
            positions = 0
        # hold 不動

    total_return = (portfolio + positions * df["close"].iloc[-1] - cash) / cash
    max_drawdown = (df["close"].cummax() - df["close"]).max() / df["close"].cummax().max()
    sharpe_ratio = (df["close"].pct_change().mean() / df["close"].pct_change().std()) * np.sqrt(252) if df["close"].pct_change().std() != 0 else 0

    return {
        "final_value": portfolio + positions * df["close"].iloc[-1],
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }

def run_daily_sim_json(df_json_list, strategy_data, cash=1_000_000, commission=0.001):
    """
    JSON list 支援每日模擬交易
    """
    df = pd.DataFrame(df_json_list)
    df = df.sort_values("date") if "date" in df.columns else df

    last_close = df["close"].iloc[-1]
    signal = strategy_data.get("signal", "hold")
    size_pct = strategy_data.get("size_pct", 0)

    if signal == "buy":
        position = cash * size_pct / last_close
        cash -= position * last_close * (1 + commission)
    elif signal == "sell":
        cash += size_pct * last_close * (1 - commission)
        position = 0
    else:
        position = 0

    return {
        "date": df["date"].iloc[-1] if "date" in df.columns else datetime.date.today().isoformat(),
        "signal": signal,
        "size_pct": size_pct,
        "price": last_close,
        "cash": cash,
        "position": position,
        "portfolio_value": cash + position * last_close
    }